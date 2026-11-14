"""The repository layer against an in-memory SQLite database (foreign keys on).

These follow the scenarios in test_changes.py, at the function level: submit
with photos, review, send to the GC, approve once, a retry gets the conflict,
the notification is written, and the work order counts a change once. No
Supabase, no DATABASE_URL.
"""

import hashlib
import os
import unittest
from datetime import timedelta

from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from db import repository
from db.database import _enforce_sqlite_foreign_keys
from db.models import (
    ApprovalDecision,
    ApprovalLink,
    Company,
    Notification,
    Project,
    User,
    utc_now,
)


def make_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(engine, "connect", _enforce_sqlite_foreign_keys)
    SQLModel.metadata.create_all(engine)
    return engine


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine()
        repository.set_engine(self.engine)
        with Session(self.engine) as s:
            self.company = Company(name="Acme")
            self.other = Company(name="Other")
            s.add_all([self.company, self.other])
            s.flush()
            cid = self.company.id
            s.add_all(
                [Project(company_id=cid, slug=slug, name=slug) for slug in ("north-park", "harbor", "cedar")]
            )
            s.add_all(
                [
                    User(company_id=cid, role="field", name="Contractor"),
                    User(company_id=cid, role="field", name="Subcontractor"),
                    User(company_id=cid, role="estimator", name="Erin Estimator"),
                    User(company_id=cid, role="manager", name="Max Manager"),
                    User(company_id=cid, role="gc", name="Gina GC", email="gc@example.com"),
                ]
            )
            s.add(Project(company_id=self.other.id, slug="north-park", name="north-park"))
            s.commit()
            self.cid = cid
            self.other_id = self.other.id

    def tearDown(self):
        repository.set_engine(None)
        self.engine.dispose()

    # helpers
    def submit(self, severity="normal", project="north-park", by="contractor", photos=None):
        self.serial = getattr(self, "serial", 0) + 1
        photos = photos or (f"photo-{self.serial}.png",)
        with repository.atomic(self.cid):
            return repository.create_change(
                "Move the outlet left", severity, list(photos), "Relocate outlet", project, by
            )

    def send(self, change, amount=123.45, days=2, scope="Relocate and test outlet"):
        with repository.atomic(self.cid):
            return repository.send_to_gc(change["id"], scope, amount, days)

    def count(self, model):
        with Session(self.engine) as s:
            return len(s.exec(select(model)).all())

    # submitting
    def test_submit_saves_photos_history_and_notifies_office(self):
        change = self.submit("high", photos=("k1.png", "k2.png", "k3.png"))
        self.assertEqual(change["photo_keys"], ["k1.png", "k2.png", "k3.png"])
        self.assertEqual(change["status"], "submitted")
        self.assertEqual(change["severity"], "high")
        self.assertEqual(change["code"], "CO-1049")
        self.assertEqual(change["author"], "Contractor")
        self.assertEqual((change["amount"], change["impact_days"]), (0, 0))
        self.assertFalse(change["sent_for_approval"])
        self.assertIsNone(change["suggestion"])
        self.assertEqual([h["kind"] for h in change["history"]], ["submitted"])
        with repository.atomic(self.cid):
            self.assertEqual(repository.list_changes(), [change])
            admin = repository.list_notifications("admin")
        # high priority alerts the estimator and the manager
        self.assertEqual(len(admin), 2)
        self.assertEqual({n["change_id"] for n in admin}, {change["id"]})
        self.assertEqual(admin[0]["msg"], "New change order submitted")

    def test_normal_priority_alerts_estimators_only_and_numbers_increase(self):
        first, second = self.submit(), self.submit()
        self.assertEqual((first["code"], second["code"]), ("CO-1049", "CO-1050"))
        with repository.atomic(self.cid):
            self.assertEqual(len(repository.list_notifications("admin")), 2)

    def test_subcontractor_label_and_title_default(self):
        with repository.atomic(self.cid):
            change = repository.create_change("x" * 100, "normal", ["a.png"], "", "harbor", "subcontractor")
        self.assertEqual((change["submitted_by"], change["author"]), ("subcontractor", "Subcontractor"))
        self.assertEqual(change["title"], "x" * 80)
        self.assertEqual(change["project_id"], "harbor")

    def test_unknown_project_is_not_found(self):
        with self.assertRaises(repository.NotFound):
            self.submit(project="nowhere")

    def test_failed_transaction_rolls_back_change_and_notices(self):
        with self.assertRaises(RuntimeError):
            with repository.atomic(self.cid):
                repository.create_change("d", "normal", ["a.png"])
                raise RuntimeError("simulated write failure")
        self.assertEqual(self.count(Notification), 0)
        with repository.atomic(self.cid):
            self.assertEqual(repository.list_changes(), [])

    # listing and filtering
    def test_list_filters_by_status_with_old_and_new_names(self):
        change = self.submit()
        self.submit()
        self.send(change)
        with repository.atomic(self.cid):
            self.assertEqual(len(repository.list_changes("submitted")), 1)
            self.assertEqual(len(repository.list_changes("awaiting_client")), 1)
            self.assertEqual(len(repository.list_changes("awaiting_gc")), 1)
            self.assertEqual(repository.list_changes("approved"), [])
            self.assertIsNone(repository.get_change("nope"))
            self.assertIsNone(repository.get_change(9999))

    # review and send
    def test_send_to_gc_freezes_terms_and_stores_only_the_token_hash(self):
        change = self.submit()
        result = self.send(change)
        self.assertEqual(result["status"], "awaiting_client")
        token = result["token"]
        with Session(self.engine) as s:
            link = s.exec(select(ApprovalLink)).one()
            self.assertEqual(link.token_hash, hashlib.sha256(token.encode()).hexdigest())
            self.assertNotIn(token, link.token_hash)
        with repository.atomic(self.cid):
            saved = repository.get_change(change["id"])
            gc_notes = repository.list_notifications("client")
            everything = [n["msg"] + (n["link_target"] or "") for n in gc_notes]
        self.assertEqual(saved["status"], "awaiting_client")
        self.assertTrue(saved["sent_for_approval"])
        self.assertEqual((saved["amount"], saved["impact_days"]), (123.45, 2))
        self.assertEqual(saved["approved_scope"], "Relocate and test outlet")
        self.assertEqual(saved["description"], "Move the outlet left")  # report not overwritten
        self.assertEqual(saved["history"][-1]["kind"], "awaiting_client")
        self.assertEqual(len(gc_notes), 1)
        self.assertEqual(gc_notes[0]["type"], "approval_requested")
        self.assertFalse(any(token in text or "token=" in text for text in everything))
        # money is stored as integer cents
        with Session(self.engine) as s:
            cents = s.execute(text("SELECT proposed_cost_cents FROM change_order_revision")).scalar_one()
        self.assertEqual(cents, 12345)

    def test_sent_terms_cannot_be_reviewed_again(self):
        change = self.submit()
        self.send(change)
        with self.assertRaises(repository.Conflict):
            self.send(change)
        with self.assertRaises(repository.Conflict):
            with repository.atomic(self.cid):
                repository.record_review(change["id"], "s", 1, 1)

    def test_fractions_of_a_cent_and_negative_amounts_are_refused(self):
        change = self.submit()
        for amount in (1.001, -1):
            with self.assertRaises(ValueError):
                self.send(change, amount=amount)
        with repository.atomic(self.cid):
            self.assertEqual(repository.get_change(change["id"])["status"], "submitted")

    def test_review_without_sending_moves_to_in_review_then_sends(self):
        change = self.submit()
        with repository.atomic(self.cid):
            self.assertEqual(repository.record_review(change["id"], None, 10, 1), {"status": "in_review"})
            repository.record_review(change["id"], "Edited scope", 20.5, 3)  # edits the draft
            saved = repository.get_change(change["id"])
        self.assertEqual((saved["status"], saved["amount"], saved["impact_days"]), ("in_review", 20.5, 3))
        self.assertFalse(saved["sent_for_approval"])
        self.assertEqual(len(saved["history"]), 2)
        result = self.send(change, 20.5, 3, "Edited scope")
        self.assertEqual(result["status"], "awaiting_client")
        with Session(self.engine) as s:
            self.assertEqual(
                s.execute(text("SELECT count(*) FROM change_order_revision")).scalar_one(), 1
            )

    def test_fast_track_authorizes_then_still_needs_the_gc(self):
        urgent = self.submit("high")
        with repository.atomic(self.cid):
            self.assertEqual(
                repository.authorize_to_proceed(urgent["id"]), {"status": "authorized_to_proceed"}
            )
            self.assertEqual(repository.work_order("north-park")["revision"], 0)
            saved = repository.get_change(urgent["id"])
        self.assertEqual(saved["status"], "authorized_to_proceed")
        self.assertEqual(saved["history"][-1]["kind"], "authorized_to_proceed")
        with self.assertRaises(repository.Conflict):  # only high priority
            with repository.atomic(self.cid):
                repository.authorize_to_proceed(self.submit()["id"])
        token = self.send(urgent)["token"]
        with repository.atomic(self.cid):
            self.assertEqual(repository.work_order("north-park")["revision"], 0)
            repository.decide(token, "approved")
            self.assertEqual(repository.work_order("north-park")["revision"], 1)

    # the GC's decision
    def test_token_lookup_and_opening_a_link_changes_nothing(self):
        change = self.submit()
        token = self.send(change)["token"]
        with repository.atomic(self.cid):
            first = repository.change_for_token(token)
            second = repository.change_for_token(token)
            self.assertIsNone(repository.change_for_token("wrong"))
        self.assertEqual(first["id"], change["id"])
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "awaiting_client")

    def test_approve_once_then_retry_conflicts_and_counts_once(self):
        change = self.submit(project="harbor", by="subcontractor", photos=("p1.png", "p2.png"))
        token = self.send(change, 123.45, 2, "Relocate and test outlet per revised plan")["token"]
        with repository.atomic(self.cid):
            self.assertEqual(repository.work_order("harbor")["revision"], 0)
            self.assertEqual(repository.decide(token, "approved"), {"status": "approved"})
        with self.assertRaises(repository.Conflict):
            with repository.atomic(self.cid):
                repository.decide(token, "approved")
        with self.assertRaises(repository.Conflict):
            with repository.atomic(self.cid):
                repository.decide(token, "rejected")
        with repository.atomic(self.cid):
            order = repository.work_order("harbor")
            saved = repository.list_changes()[0]
            contractor = repository.list_notifications("contractor")
            self.assertEqual(repository.work_order("harbor"), order)
            self.assertEqual(repository.work_order("cedar")["revision"], 0)
            self.assertEqual(repository.work_order("unknown")["changes"], [])
        self.assertEqual(
            (order["revision"], order["additional_amount"], order["additional_days"]), (1, 123.45, 2)
        )
        self.assertEqual(order["changes"][0]["scope"], "Relocate and test outlet per revised plan")
        self.assertEqual(order["changes"][0]["photo_keys"], ["p1.png", "p2.png"])
        self.assertEqual(order["changes"][0]["change_id"], change["id"])
        self.assertEqual(order["changes"][0]["amount"], 123.45)
        self.assertEqual(saved["status"], "approved")
        self.assertEqual(saved["submitted_by"], "subcontractor")
        self.assertEqual(saved["title"], "Relocate outlet")
        self.assertEqual(len(saved["history"]), 3)
        self.assertEqual([h["kind"] for h in saved["history"]], ["submitted", "awaiting_client", "approved"])
        # the decision wrote its notification in the same transaction
        self.assertEqual([n["msg"] for n in contractor], ["Change approved; work order updated"])
        with repository.atomic(self.cid):
            admin = [n for n in repository.list_notifications("admin") if n["type"] == "change_approved"]
        self.assertEqual(len(admin), 2)  # the estimator and the manager
        self.assertEqual(self.count(ApprovalDecision), 1)

    def test_decline_does_not_update_the_work_order(self):
        change = self.submit()
        token = self.send(change, 500, 1)["token"]
        with repository.atomic(self.cid):
            self.assertEqual(repository.decide(token, "declined"), {"status": "rejected"})
            self.assertEqual(repository.work_order("north-park")["revision"], 0)
            self.assertEqual(repository.get_change(change["id"])["status"], "rejected")
        with self.assertRaises(repository.Conflict):
            with repository.atomic(self.cid):
                repository.decide(token, "approved")

    def test_conflict_rolls_back_everything_the_retry_wrote(self):
        change = self.submit()
        token = self.send(change)["token"]
        with repository.atomic(self.cid):
            repository.decide(token, "approved")
        before = self.count(Notification)
        with self.assertRaises(repository.Conflict):
            with repository.atomic(self.cid):
                repository.decide(token, "approved")
        self.assertEqual(self.count(Notification), before)

    def test_invalid_expired_and_revoked_links(self):
        change = self.submit()
        token = self.send(change)["token"]
        with self.assertRaises(repository.NotFound):
            with repository.atomic(self.cid):
                repository.decide("not-a-token", "approved")
        # a new link revokes the old one
        with repository.atomic(self.cid):
            fresh = repository.issue_client_token(change["id"])
            self.assertIsNone(repository.change_for_token(token))
            self.assertIsNotNone(repository.change_for_token(fresh))
        with Session(self.engine) as s:
            self.assertEqual(
                sorted(link.revoked_at is None for link in s.exec(select(ApprovalLink)).all()),
                [False, True],
            )
        # an expired link is not valid
        with Session(self.engine) as s:
            link = s.exec(select(ApprovalLink).where(ApprovalLink.revoked_at == None)).one()  # noqa: E711
            link.expires_at = utc_now() - timedelta(minutes=1)
            s.add(link)
            s.commit()
        with repository.atomic(self.cid):
            self.assertIsNone(repository.change_for_token(fresh))
        with self.assertRaises(repository.NotFound):
            with repository.atomic(self.cid):
                repository.decide(fresh, "approved")

    # suggestions
    def test_ai_suggestion_is_saved_but_changes_nothing_else(self):
        change = self.submit()
        advice = dict(
            scope="Move and test outlet",
            amount=200,
            impact_days=1,
            rationale="Assumes existing wiring is adequate",
            in_scope=False,
        )
        with repository.atomic(self.cid):
            repository.save_suggestion(change["id"], advice, "Replace kitchen cabinetry only")
            saved = repository.get_change(change["id"])
            self.assertEqual(repository.work_order("north-park")["revision"], 0)
        self.assertEqual(saved["suggestion"], advice)
        self.assertEqual(saved["original_scope"], "Replace kitchen cabinetry only")
        self.assertEqual((saved["amount"], saved["status"]), (0, "submitted"))
        self.send(change)
        with self.assertRaises(repository.Conflict):
            with repository.atomic(self.cid):
                repository.save_suggestion(change["id"], advice, "Replace kitchen cabinetry only")

    # notifications and history helpers
    def test_notify_and_add_event_write_rows(self):
        change = self.submit()
        with repository.atomic(self.cid):
            repository.notify("client", change["id"], "hello", "approval_requested")
            repository.notify("contractor", change["id"], "for the submitter", "change_in_review")
            entry = repository.add_event(change, "approved", "Done", "Someone")
            self.assertEqual(len(repository.list_notifications("client")), 1)
            self.assertEqual(len(repository.list_notifications("contractor")), 1)
            self.assertEqual(repository.list_notifications("nobody"), [])
        self.assertEqual((entry["kind"], entry["person"], entry["changeId"]), ("approved", "Someone", change["id"]))
        self.assertEqual(change["history"][-1], entry)

    def test_notification_with_a_token_link_is_refused_by_the_schema(self):
        change = self.submit()
        with self.assertRaises(IntegrityError):
            with repository.atomic(self.cid):
                repository.notify("client", change["id"], "http://x/approve?token=abc", "approval_requested")

    # tenants
    def test_every_query_is_limited_to_the_company(self):
        change = self.submit()
        token = self.send(change)["token"]
        with repository.atomic(self.other_id):
            self.assertEqual(repository.list_changes(), [])
            self.assertIsNone(repository.get_change(change["id"]))
            self.assertIsNone(repository.change_for_token(token))
            self.assertEqual(repository.work_order("north-park")["revision"], 0)
            self.assertEqual(repository.list_notifications("admin"), [])
            with self.assertRaises(repository.NotFound):
                repository.record_review(change["id"], None, 1, 1)
            with self.assertRaises(repository.NotFound):
                repository.decide(token, "approved")
            with self.assertRaises(repository.NotFound):  # no field user in this company
                repository.create_change("d", "normal", ["z.png"])

    def test_functions_need_a_transaction(self):
        with self.assertRaises(RuntimeError):
            repository.list_changes()

    def test_default_company_comes_from_the_setting(self):
        self.submit()
        with unittest_env(WORKSPACE_COMPANY_ID=str(self.cid)):
            with repository.atomic():
                self.assertEqual(len(repository.list_changes()), 1)
        with unittest_env(WORKSPACE_COMPANY_ID=str(self.other_id)):
            with repository.atomic():
                self.assertEqual(repository.list_changes(), [])


class unittest_env:
    """Set environment variables for a with-block."""

    def __init__(self, **values):
        self.values, self.saved = values, {}

    def __enter__(self):
        for key, value in self.values.items():
            self.saved[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, *_):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class SelectorTests(unittest.TestCase):
    def test_default_is_the_sqlite_prototype_store(self):
        from db import store_selector

        with unittest_env(WORKSPACE_BACKEND="sqlite"):
            self.assertEqual(store_selector.backend_name(), "sqlite")
            self.assertEqual(store_selector.load_store().__name__, "services.store")

    def test_postgres_selects_the_repository(self):
        from db import store_selector

        with unittest_env(WORKSPACE_BACKEND="postgres"):
            self.assertIs(store_selector.load_store(), repository)

    def test_unknown_backend_is_refused(self):
        from db import store_selector

        with unittest_env(WORKSPACE_BACKEND="mongo"):
            with self.assertRaises(RuntimeError):
                store_selector.backend_name()

    def test_every_public_store_function_has_a_repository_equivalent(self):
        from services import store

        for name in ("atomic", "notify", "add_event", "create_change", "issue_client_token",
                     "change_for_token", "work_order", "now"):
            self.assertTrue(callable(getattr(repository, name)), name)
            self.assertTrue(callable(getattr(store, name)), name)

if __name__ == "__main__":
    unittest.main()
