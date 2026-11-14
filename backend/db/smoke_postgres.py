"""Opt-in smoke test of the repository against a real database. Not a unittest.

CI never runs this file. It runs the whole workflow through db.repository
against whatever DATABASE_URL points to, inside ONE outer transaction that is
always rolled back, so nothing stays in the database, even on success.
Each repository call runs in a savepoint of that outer transaction.

Run it from backend (needs psycopg2-binary installed and DATABASE_URL set in
the environment or backend/.env loaded by your shell):

    python -m db.smoke_postgres --yes-use-real-database

It refuses to run without that flag. It assumes the seeded company "Cohyric
Demo" (id 1) with the project "north-park" and field, estimator, manager and
gc users. It prints one line per step and a summary, and never prints
DATABASE_URL, tokens or row contents beyond ids and statuses.

To test the script itself without any server:

    python -m db.smoke_postgres --sqlite-memory

That builds the schema in memory with SQLModel.metadata.create_all, seeds a
minimal company, project and users, and runs the same steps.
"""

import argparse
import sys
import uuid

from sqlalchemy import event, func
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from . import repository
from .database import _enforce_sqlite_foreign_keys, get_engine
from .models import ChangeEvent, Company, Notification, Project, User

COMPANY_ID = 1
COMPANY_NAME = "Cohyric Demo"
PROJECT = "north-park"
AMOUNT, DAYS = 123.45, 2


def _sqlite_memory_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(engine, "connect", _enforce_sqlite_foreign_keys)

    # pysqlite needs this for SAVEPOINT to work (SQLAlchemy documents the recipe).
    @event.listens_for(engine, "connect")
    def _no_implicit_begin(dbapi_connection, _record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(connection):
        connection.exec_driver_sql("BEGIN")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Company(id=COMPANY_ID, name=COMPANY_NAME))
        s.flush()
        s.add(Project(company_id=COMPANY_ID, slug=PROJECT, name=PROJECT))
        for role in ("field", "estimator", "manager", "gc"):
            s.add(User(company_id=COMPANY_ID, role=role, name=role.title(), email=f"{role}@example.com"))
        s.commit()
    return engine


def _row_counts(engine) -> dict[str, int]:
    """Row counts of every table, read on a separate connection."""
    with Session(engine) as s:
        return {
            table.name: s.execute(select(func.count()).select_from(table)).scalar_one()
            for table in SQLModel.metadata.sorted_tables
        }


class Run:
    def __init__(self) -> None:
        self.failed = 0
        self.state: dict = {}

    def step(self, name: str, action) -> None:
        try:
            detail = action()
        except Exception as error:  # report, keep going where later steps can still run
            self.failed += 1
            # Only the error's class and, for the repository's own errors, its message:
            # a database error's text can contain statement values.
            own = isinstance(error, (repository.NotFound, repository.Conflict, ValueError))
            print(f"FAIL {name}: {type(error).__name__}{': ' + str(error) if own else ''}")
            return
        print(f"OK   {name}" + (f" ({detail})" if detail else ""))

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)


def run_steps(run: Run) -> None:
    state = run.state
    suffix = uuid.uuid4().hex[:12]

    def check_company():
        with repository.atomic(COMPANY_ID):
            session = repository._ctx().session
            company = session.get(Company, COMPANY_ID)
            run.expect(company is not None and company.name == COMPANY_NAME, f'company {COMPANY_ID} is not "{COMPANY_NAME}"')
        return f"company {COMPANY_ID}"

    def create():
        with repository.atomic(COMPANY_ID):
            before = repository.work_order(PROJECT)
            state["before"] = before["revision"]
            change = repository.create_change(
                "Smoke test change",
                "high",
                [f"smoke-{suffix}-1.png", f"smoke-{suffix}-2.png"],
                "Smoke test",
                PROJECT,
            )
        run.expect(len(change["photo_keys"]) == 2, "two photos expected")
        state["id"] = change["id"]
        return f"change {change['id']}, status {change['status']}"

    def authorize():
        with repository.atomic(COMPANY_ID):
            return f"status {repository.authorize_to_proceed(state['id'])['status']}"

    def review():
        with repository.atomic(COMPANY_ID):
            return f"status {repository.record_review(state['id'], 'Smoke scope', AMOUNT, DAYS)['status']}"

    def send():
        with repository.atomic(COMPANY_ID):
            result = repository.send_to_gc(state["id"], "Smoke scope", AMOUNT, DAYS)
        state["token"] = result["token"]
        return f"status {result['status']}"

    def open_link():
        # No company named: the link fixes it, as for a GC who is not signed in.
        with repository.atomic():
            change = repository.change_for_token(state["token"])
            run.expect(change is not None and change["id"] == state["id"], "link did not resolve")
            return f"status {change['status']}"

    def approve():
        with repository.atomic():
            return f"status {repository.decide(state['token'], 'approved')['status']}"

    def order():
        with repository.atomic(COMPANY_ID):
            result = repository.work_order(PROJECT)
        ids = [c["change_id"] for c in result["changes"]]
        run.expect(ids.count(state["id"]) == 1, "change must appear exactly once")
        run.expect(result["revision"] == state["before"] + 1, "revision must grow by exactly one")
        return f"revision {result['revision']}"

    def retry():
        try:
            with repository.atomic():
                repository.decide(state["token"], "approved")
        except repository.Conflict:
            return "Conflict, as expected"
        raise AssertionError("a second decision was accepted")

    def notices():
        with repository.atomic(COMPANY_ID):
            session = repository._ctx().session
            rows = session.exec(
                select(Notification, User)
                .join(User, (User.company_id == Notification.company_id) & (User.id == Notification.recipient_user_id))
                .where(Notification.company_id == COMPANY_ID)
                .where(Notification.report_id == int(state["id"]))
            ).all()
            roles = {user.role for _n, user in rows}
            count = len(rows)
        run.expect({"field", "estimator", "manager"} <= roles, f"missing recipient roles; got {sorted(roles)}")
        return f"{count} notifications for roles {', '.join(sorted(roles))}"

    for name, action in (
        ("seeded company exists", check_company),
        ("create_change (high priority, 2 photos)", create),
        ("authorize_to_proceed", authorize),
        ("record_review", review),
        ("send_to_gc", send),
        ("change_for_token", open_link),
        ("decide approved", approve),
        ("work_order counts it once", order),
        ("second decide raises Conflict", retry),
        ("notifications for submitter, estimators, managers", notices),
    ):
        if name != "seeded company exists" and "id" not in state and name != "create_change (high priority, 2 photos)":
            print(f"SKIP {name}: no change was created")
            run.failed += 1
            continue
        run.step(name, action)
        if name == "seeded company exists" and run.failed:
            return


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--yes-use-real-database", action="store_true", help="run against DATABASE_URL")
    parser.add_argument("--sqlite-memory", action="store_true", help="run against a throwaway in-memory SQLite")
    args = parser.parse_args(argv)
    if args.sqlite_memory:
        engine = _sqlite_memory_engine()
        target = "in-memory SQLite"
    elif args.yes_use_real_database:
        engine = get_engine()
        target = "the database in DATABASE_URL"
    else:
        print("Refusing to run: pass --yes-use-real-database (or --sqlite-memory).", file=sys.stderr)
        return 2

    print(f"Smoke test against {target}; everything is rolled back at the end.")
    before = _row_counts(engine)
    run = Run()
    connection = engine.connect()
    outer = connection.begin()
    repository.set_engine(connection)
    try:
        run_steps(run)
    finally:
        repository.set_engine(None)
        outer.rollback()
        connection.close()
    after = _row_counts(engine)
    clean = before == after
    print(f"{'OK  ' if clean else 'FAIL'} rollback: row counts {'unchanged' if clean else 'CHANGED'}")
    if not clean:
        run.failed += 1
    print(f"Summary: {'all steps passed' if not run.failed else str(run.failed) + ' problem(s)'}")
    return 1 if run.failed else 0


if __name__ == "__main__":
    sys.exit(main())
