"""The repository layer against an in-memory SQLite database (foreign keys on).

These follow the scenarios in test_changes.py, at the function level: submit
with photos, review, send to the GC, approve once, a retry gets the conflict,
the notification is written, and the work order counts a change once. No
Supabase, no DATABASE_URL.
"""

import hashlib
import os
import unittest
import uuid
from datetime import datetime, timedelta

from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from db import repository
from db.repository import default_company_id
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
from schemas.changes import WorkspaceChangeOut


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

    # terms, currency and authorization in the change dict (WorkspaceChangeOut)
    def test_new_change_has_no_terms_and_no_authorization(self):
        change = self.submit("high")
        for key in ("proposed_cost_cents", "requested_timeline_days", "authorized_at", "authorized_by"):
            self.assertIn(key, change)
            self.assertIsNone(change[key], key)
        self.assertEqual(change["currency"], "USD")
        self.assertEqual((change["amount"], change["impact_days"]), (0, 0))
        WorkspaceChangeOut.model_validate(change)

    def test_terms_and_currency_appear_after_review_and_on_the_gc_link(self):
        change = self.submit()
        with repository.atomic(self.cid):
            repository.record_review(
                change["id"], "Draft scope", impact_days=2, proposed_cost_cents=12345, currency="CAD"
            )
            draft = repository.get_change(change["id"])
        self.assertEqual(draft["status"], "in_review")
        self.assertEqual(
            (draft["proposed_cost_cents"], draft["requested_timeline_days"], draft["currency"]),
            (12345, 2, "CAD"),
        )
        # the dollar fields the app still reads say the same thing
        self.assertEqual((draft["amount"], draft["impact_days"]), (123.45, 2))
        self.assertIsNone(draft["authorized_at"])
        self.assertIsNone(draft["authorized_by"])
        # every field of the API's response model is in the dict, by the same name
        self.assertLessEqual(set(WorkspaceChangeOut.model_fields), set(draft))
        WorkspaceChangeOut.model_validate(draft)

        with repository.atomic(self.cid):
            token = repository.send_to_gc(
                change["id"], "Final scope", impact_days=3, proposed_cost_cents=20050, currency="EUR"
            )["token"]
        with repository.atomic():  # as the GC: no company named
            seen = repository.change_for_token(token)
        self.assertEqual(
            (seen["proposed_cost_cents"], seen["requested_timeline_days"], seen["currency"]),
            (20050, 3, "EUR"),
        )
        self.assertEqual((seen["amount"], seen["impact_days"], seen["approved_scope"]), (200.5, 3, "Final scope"))
        self.assertEqual(seen["status"], "awaiting_client")  # legacy name, unchanged
        WorkspaceChangeOut.model_validate(seen)
        with Session(self.engine) as s:
            row = s.execute(
                text("SELECT proposed_cost_cents, currency, requested_timeline_days FROM change_order_revision")
            ).one()
        self.assertEqual(tuple(row), (20050, "EUR", 3))

    def test_currency_defaults_to_usd_and_the_dollars_path_still_works(self):
        change = self.submit()
        self.send(change, amount=123.45, days=2)
        with repository.atomic(self.cid):
            saved = repository.get_change(change["id"])
        self.assertEqual(
            (saved["proposed_cost_cents"], saved["currency"], saved["amount"]), (12345, "USD", 123.45)
        )

    def test_integer_cents_are_stored_exactly_without_a_float(self):
        change = self.submit()
        exact = 9_007_199_254_740_993  # 2**53 + 1: a float cannot hold this
        self.assertNotEqual(int(float(exact)), exact)
        with repository.atomic(self.cid):
            repository.record_review(change["id"], None, impact_days=0, proposed_cost_cents=exact)
            self.assertEqual(repository.get_change(change["id"])["proposed_cost_cents"], exact)

    def test_currency_and_cents_are_validated_and_nothing_is_saved(self):
        change = self.submit()
        for currency in ("usd", "US", "USDX", "U$D", "US1", " USD", "USD\n", "", None, 840):
            with self.subTest(currency=currency):
                with self.assertRaises(ValueError):
                    with repository.atomic(self.cid):
                        repository.record_review(change["id"], "s", 10, 1, currency=currency)
                if currency is None:
                    continue  # send_to_gc reads None as "not given": USD, or the draft's
                with self.assertRaises(ValueError):
                    with repository.atomic(self.cid):
                        repository.send_to_gc(change["id"], "s", 10, 1, currency=currency)
        for cents in (-1, 10.5, "100", True):
            with self.subTest(cents=cents):
                with self.assertRaises(ValueError):
                    with repository.atomic(self.cid):
                        repository.record_review(change["id"], "s", impact_days=1, proposed_cost_cents=cents)
        with self.assertRaises(ValueError):  # dollars and cents that disagree
            with repository.atomic(self.cid):
                repository.send_to_gc(change["id"], "s", 10, 1, proposed_cost_cents=1001)
        with repository.atomic(self.cid):
            saved = repository.get_change(change["id"])
        self.assertEqual(saved["status"], "submitted")
        self.assertIsNone(saved["proposed_cost_cents"])
        self.assertEqual(self.count(ApprovalLink), 0)
        with Session(self.engine) as s:
            self.assertEqual(s.execute(text("SELECT count(*) FROM change_order_revision")).scalar_one(), 0)
        # dollars and cents that agree are accepted
        with repository.atomic(self.cid):
            repository.record_review(change["id"], "s", 10, 1, proposed_cost_cents=1000)
            self.assertEqual(repository.get_change(change["id"])["proposed_cost_cents"], 1000)

    # one currency per project
    def review(self, change, currency="USD", cents=1000, days=1, company=None):
        with repository.atomic(self.cid if company is None else company):
            return repository.record_review(
                change["id"], "Scope", impact_days=days, proposed_cost_cents=cents, currency=currency
            )

    def project_currency(self, slug="north-park", company=None):
        with Session(self.engine) as s:
            return s.exec(
                select(Project.currency)
                .where(Project.slug == slug)
                .where(Project.company_id == (self.cid if company is None else company))
            ).one()

    def test_second_currency_is_refused_for_the_same_project(self):
        first, second = self.submit(), self.submit()
        self.review(first, "CAD")
        self.assertEqual(self.project_currency(), "CAD")  # the first saved terms set it
        self.assertTrue(issubclass(repository.CurrencyMismatch, repository.Conflict))  # HTTP 409
        with self.assertRaises(repository.CurrencyMismatch) as refused:
            self.review(second)  # the USD default is a second currency here
        self.assertIn("CAD", str(refused.exception))
        self.assertIn("USD", str(refused.exception))
        with self.assertRaises(repository.CurrencyMismatch):
            with repository.atomic(self.cid):
                repository.send_to_gc(second["id"], "Scope", 10, 1, currency="EUR")
        with self.assertRaises(repository.CurrencyMismatch):
            with repository.atomic(self.cid):
                repository.send_to_gc(second["id"], "Scope", 10, 1)  # USD when left out
        # nothing was saved for the refused change, and the project did not move
        with repository.atomic(self.cid):
            saved = repository.get_change(second["id"])
        self.assertEqual((saved["status"], saved["proposed_cost_cents"]), ("submitted", None))
        self.assertEqual(self.count(ApprovalLink), 0)
        self.assertEqual(self.project_currency(), "CAD")
        with Session(self.engine) as s:
            self.assertEqual(s.execute(text("SELECT count(*) FROM change_order_revision")).scalar_one(), 1)
        # the project's own currency is accepted, on a draft and on a send
        self.review(second, "CAD")
        with repository.atomic(self.cid):
            repository.send_to_gc(second["id"], "Scope", impact_days=1, proposed_cost_cents=500, currency="CAD")
            self.assertEqual(repository.get_change(second["id"])["currency"], "CAD")
        # a sent change still pins the currency for the changes that follow
        with self.assertRaises(repository.CurrencyMismatch):
            self.review(first, "USD")

    def test_other_projects_and_companies_keep_their_own_currency(self):
        self.review(self.submit(project="north-park"), "CAD")
        harbor = self.submit(project="harbor")
        self.review(harbor)  # USD default, in another project of the same company
        self.assertEqual((self.project_currency("north-park"), self.project_currency("harbor")), ("CAD", "USD"))
        with self.assertRaises(repository.CurrencyMismatch):
            self.review(self.submit(project="harbor"), "CAD")
        # another company's project with the same slug is a different project
        self.seed_other_company()
        with repository.atomic(self.other_id):
            theirs = repository.create_change("Other job", "normal", ["theirs.png"], "T", "north-park")
        self.review(theirs, "EUR", company=self.other_id)
        self.assertEqual(self.project_currency("north-park", self.other_id), "EUR")
        self.assertEqual(self.project_currency("north-park"), "CAD")
        self.assertEqual(self.project_currency("cedar"), "USD")  # untouched

    def test_usd_default_works_for_every_change_of_a_project(self):
        tokens = []
        for cents in (10000, 2550):
            change = self.submit()
            with repository.atomic(self.cid):
                repository.record_review(change["id"], "Scope", impact_days=1, proposed_cost_cents=cents)
                tokens.append(repository.send_to_gc(change["id"], "Scope", cents / 100, 1)["token"])
        with repository.atomic(self.cid):
            for token in tokens:
                repository.decide(token, "approved")
            order = repository.work_order("north-park")
            self.assertEqual({c["currency"] for c in repository.list_changes()}, {"USD"})
        self.assertEqual(
            (order["currency"], order["revision"], order["additional_amount"]), ("USD", 2, 125.5)
        )
        self.assertEqual(self.project_currency(), "USD")

    def test_work_order_returns_the_project_currency(self):
        change = self.submit(project="harbor")
        with repository.atomic(self.cid):
            token = repository.send_to_gc(
                change["id"], "Scope", impact_days=2, proposed_cost_cents=4200, currency="CAD"
            )["token"]
            repository.decide(token, "approved")
            order = repository.work_order("harbor")
            self.assertEqual(repository.work_order("cedar")["currency"], "USD")  # nothing reviewed yet
            self.assertEqual(repository.work_order("unknown")["currency"], "USD")
        self.assertEqual((order["currency"], order["additional_amount"], order["revision"]), ("CAD", 42.0, 1))
        # the keys the app already reads are all still there
        self.assertLessEqual(
            {"project_id", "revision", "additional_amount", "additional_days", "changes"}, set(order)
        )

    def test_only_draft_of_a_project_may_still_change_currency(self):
        first = self.submit()
        self.review(first, "CAD")
        self.review(first, "EUR")  # no other terms in the project yet: a correction
        self.assertEqual(self.project_currency(), "EUR")
        with repository.atomic(self.cid):
            self.assertEqual(repository.get_change(first["id"])["currency"], "EUR")
        self.review(self.submit(), "EUR")
        with self.assertRaises(repository.CurrencyMismatch):  # now a second change holds EUR
            self.review(first, "CAD")
        self.assertEqual(self.project_currency(), "EUR")

    def test_project_with_a_base_budget_keeps_its_currency(self):
        with Session(self.engine) as s:
            project = s.exec(
                select(Project).where(Project.slug == "cedar").where(Project.company_id == self.cid)
            ).one()
            project.base_budget_cents = 5_000_000
            s.add(project)
            s.commit()
        change = self.submit(project="cedar")
        with self.assertRaises(repository.CurrencyMismatch):  # the budget is already in USD
            self.review(change, "CAD")
        self.review(change)
        self.assertEqual(self.project_currency("cedar"), "USD")

    def test_work_order_refuses_to_add_up_two_currencies(self):
        change = self.submit()
        token = self.send(change)["token"]
        with repository.atomic(self.cid):
            repository.decide(token, "approved")
        with Session(self.engine) as s:  # only reachable by editing the data directly
            s.execute(text("UPDATE change_order_revision SET currency = 'CAD'"))
            s.commit()
        with self.assertRaises(repository.CurrencyMismatch):
            with repository.atomic(self.cid):
                repository.work_order("north-park")

    # sending without terms keeps the draft
    def test_send_without_terms_keeps_the_draft(self):
        change = self.submit()
        with repository.atomic(self.cid):
            repository.record_review(change["id"], "Draft scope", impact_days=2, proposed_cost_cents=12345)
            token = repository.send_to_gc(change["id"])["token"]
        with repository.atomic():
            seen = repository.change_for_token(token)
        self.assertEqual(
            (seen["proposed_cost_cents"], seen["requested_timeline_days"], seen["currency"]),
            (12345, 2, "USD"),
        )
        self.assertEqual((seen["amount"], seen["impact_days"]), (123.45, 2))
        self.assertEqual(seen["approved_scope"], "Draft scope")
        self.assertEqual(seen["status"], "awaiting_client")
        self.assertTrue(seen["sent_for_approval"])
        with Session(self.engine) as s:
            self.assertEqual(s.execute(text("SELECT count(*) FROM change_order_revision")).scalar_one(), 1)
        with repository.atomic():
            repository.decide(token, "approved")
            self.assertEqual(repository.work_order("north-park")["additional_amount"], 123.45)

    def test_send_without_terms_keeps_the_draft_currency_and_takes_a_new_scope(self):
        change = self.submit()
        self.review(change, "CAD", cents=7700, days=5)
        with self.assertRaises(repository.CurrencyMismatch):  # a currency without a cost
            with repository.atomic(self.cid):
                repository.send_to_gc(change["id"], currency="EUR")
        with repository.atomic(self.cid):
            repository.send_to_gc(change["id"], "Scope for the GC", None, None, "Erin Estimator")
            sent = repository.get_change(change["id"])
        self.assertEqual(
            (sent["proposed_cost_cents"], sent["requested_timeline_days"], sent["currency"]),
            (7700, 5, "CAD"),
        )
        self.assertEqual(sent["approved_scope"], "Scope for the GC")
        self.assertEqual(sent["history"][-1]["person"], "Erin Estimator")

    def test_send_with_terms_still_replaces_the_draft(self):
        cases = (
            (dict(amount=0, impact_days=0), (0, 0)),  # an explicit zero is terms
            (dict(amount=50), (5000, 0)),
            (dict(impact_days=4), (0, 4)),
            (dict(proposed_cost_cents=250, impact_days=1), (250, 1)),
        )
        for terms, expected in cases:
            with self.subTest(terms=terms):
                change = self.submit()
                self.review(change, cents=12345, days=2)
                with repository.atomic(self.cid):
                    repository.send_to_gc(change["id"], **terms)
                    sent = repository.get_change(change["id"])
                self.assertEqual((sent["proposed_cost_cents"], sent["requested_timeline_days"]), expected)
                self.assertEqual(sent["approved_scope"], "Move the outlet left")  # as before: the report

    def test_send_without_terms_and_without_a_draft_is_unchanged(self):
        change = self.submit()
        with repository.atomic(self.cid):
            repository.send_to_gc(change["id"])
            sent = repository.get_change(change["id"])
        self.assertEqual(
            (sent["proposed_cost_cents"], sent["requested_timeline_days"], sent["currency"]), (0, 0, "USD")
        )
        self.assertEqual(sent["approved_scope"], "Move the outlet left")

    def test_authorization_fields_appear_after_fast_track_and_stay(self):
        urgent = self.submit("high")
        with Session(self.engine) as s:
            second = User(company_id=self.cid, role="manager", name="Second Manager")
            s.add(second)
            s.commit()
            second_id = second.id
        before = utc_now()
        with repository.atomic(self.cid):
            repository.authorize_to_proceed(urgent["id"], actor_name="Second Manager", actor_user_id=second_id)
            saved = repository.get_change(urgent["id"])
        self.assertEqual(saved["status"], "authorized_to_proceed")
        self.assertEqual(saved["authorized_by"], "Second Manager")
        stamp = datetime.fromisoformat(saved["authorized_at"])
        self.assertIsNotNone(stamp.tzinfo)
        self.assertLess(abs(stamp - before), timedelta(minutes=1))
        # authorizing is not an estimate: no terms yet
        self.assertIsNone(saved["proposed_cost_cents"])
        self.assertIsNone(saved["requested_timeline_days"])
        self.assertEqual(saved["currency"], "USD")
        WorkspaceChangeOut.model_validate(saved)

        with repository.atomic(self.cid):
            repository.record_review(urgent["id"], "s", impact_days=4, proposed_cost_cents=99900)
            reviewed = repository.get_change(urgent["id"])
            token = repository.send_to_gc(urgent["id"], "s", impact_days=4, proposed_cost_cents=99900)["token"]
            self.assertEqual(repository.decide(token, "declined"), {"status": "rejected"})
            final = repository.get_change(urgent["id"])
        self.assertEqual(reviewed["status"], "authorized_to_proceed")
        self.assertEqual((reviewed["proposed_cost_cents"], reviewed["requested_timeline_days"]), (99900, 4))
        self.assertEqual(final["status"], "rejected")  # legacy name, unchanged
        for change in (reviewed, final):
            self.assertEqual(
                (change["authorized_by"], change["authorized_at"]),
                ("Second Manager", saved["authorized_at"]),
            )
        WorkspaceChangeOut.model_validate(final)

    def test_default_authorizer_is_the_first_manager(self):
        urgent = self.submit("high")
        with repository.atomic(self.cid):
            repository.authorize_to_proceed(urgent["id"])
            self.assertEqual(repository.get_change(urgent["id"])["authorized_by"], "Max Manager")

    def test_legacy_status_names_are_unchanged(self):
        sent, declined = self.submit(), self.submit()
        self.send(sent)
        token = self.send(declined)["token"]
        with repository.atomic(self.cid):
            self.assertEqual(repository.decide(token, "rejected"), {"status": "rejected"})
            statuses = [c["status"] for c in repository.list_changes()]
            kinds = [h["kind"] for c in repository.list_changes() for h in c["history"]]
            self.assertEqual(len(repository.list_changes("awaiting_client")), 1)
            self.assertEqual(len(repository.list_changes("rejected")), 1)
        self.assertEqual(statuses, ["awaiting_client", "rejected"])
        self.assertEqual(kinds, ["submitted", "awaiting_client", "submitted", "awaiting_client", "rejected"])
        self.assertNotIn("awaiting_gc", statuses + kinds)
        self.assertNotIn("declined", statuses + kinds)
        with Session(self.engine) as s:  # the database holds the v2 names
            stored = [r[0] for r in s.execute(text("SELECT status FROM change_event ORDER BY id"))]
        self.assertEqual(stored, ["awaiting_gc", "declined"])

    # sign-in: the caller behind a Supabase user id
    def seed_callers(self):
        ids = {name: uuid.uuid4() for name in ("field", "estimator", "other")}
        with Session(self.engine) as s:
            for user in s.exec(select(User).where(User.company_id == self.cid)).all():
                if user.name == "Contractor":
                    user.auth_user_id = ids["field"]
                elif user.role == "estimator":
                    user.auth_user_id = ids["estimator"]
                s.add(user)
            s.add(User(company_id=self.other_id, role="manager", name="Other Manager", auth_user_id=ids["other"]))
            s.commit()
        return ids

    def test_caller_for_auth_user_finds_the_user_across_companies(self):
        ids = self.seed_callers()
        # outside atomic(): it opens its own session
        field = repository.caller_for_auth_user(str(ids["field"]))
        self.assertEqual(set(field), {"id", "company_id", "role", "name"})
        self.assertEqual((field["company_id"], field["role"], field["name"]), (self.cid, "field", "Contractor"))
        self.assertIsInstance(field["id"], int)
        estimator = repository.caller_for_auth_user(str(ids["estimator"]))
        self.assertEqual((estimator["company_id"], estimator["role"]), (self.cid, "estimator"))
        # the company comes from the row, not from a setting or the transaction
        other = repository.caller_for_auth_user(str(ids["other"]))
        self.assertEqual((other["company_id"], other["role"], other["name"]), (self.other_id, "manager", "Other Manager"))
        with unittest_env(WORKSPACE_COMPANY_ID=str(self.cid)):
            self.assertEqual(repository.caller_for_auth_user(str(ids["other"])), other)
        with repository.atomic(self.cid):
            self.assertEqual(repository.caller_for_auth_user(str(ids["other"])), other)
            self.assertEqual(repository._ctx().company_id, self.cid)  # the transaction is not moved
        # other spellings of the same UUID
        self.assertEqual(repository.caller_for_auth_user(str(ids["field"]).upper()), field)
        self.assertEqual(repository.caller_for_auth_user(ids["field"]), field)

    def test_caller_id_and_company_drive_a_submission(self):
        ids = self.seed_callers()
        caller = repository.caller_for_auth_user(str(ids["field"]))
        with repository.atomic(caller["company_id"]):
            change = repository.create_change(
                "d", "normal", ["caller.png"], submitted_by_user_id=caller["id"]
            )
        self.assertEqual(change["author"], caller["name"])

    def test_caller_for_auth_user_is_none_for_unknown_or_malformed_ids(self):
        self.seed_callers()
        for value in (str(uuid.uuid4()), "not-a-uuid", "", "1", "' OR 1=1 --", None, 42, b"x"):
            with self.subTest(value=value):
                self.assertIsNone(repository.caller_for_auth_user(value))

    def test_caller_for_auth_user_never_returns_a_gc(self):
        # The schema refuses a gc with an account; the lookup refuses one too.
        gc_id = uuid.uuid4()
        with Session(self.engine) as s:
            with self.assertRaises(IntegrityError):
                s.add(User(company_id=self.cid, role="gc", name="GC With Account", auth_user_id=gc_id))
                s.commit()
        with Session(self.engine) as s:
            s.execute(text("PRAGMA ignore_check_constraints = ON"))
            s.add(User(company_id=self.cid, role="gc", name="GC With Account", auth_user_id=gc_id))
            s.commit()
            s.execute(text("PRAGMA ignore_check_constraints = OFF"))
            self.assertEqual(len(s.exec(select(User).where(User.auth_user_id == gc_id)).all()), 1)
        self.assertIsNone(repository.caller_for_auth_user(str(gc_id)))

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

    # the caller as submitter
    def test_given_field_user_is_the_submitter(self):
        with Session(self.engine) as s:
            sub = s.exec(select(User).where(User.name == "Subcontractor")).one().id
        with repository.atomic(self.cid):
            change = repository.create_change(
                "d", "normal", ["by-id.png"], "t", "harbor", "contractor", submitted_by_user_id=sub
            )
        self.assertEqual(change["author"], "Subcontractor")
        with Session(self.engine) as s:
            self.assertEqual(s.execute(text("SELECT submitted_by_id FROM change_event")).scalar_one(), sub)

    def test_submitter_from_another_company_or_wrong_role_is_refused(self):
        with Session(self.engine) as s:
            foreign = User(company_id=self.other_id, role="field", name="Foreign")
            s.add(foreign)
            s.commit()
            foreign_id = foreign.id
            estimator = s.exec(select(User).where(User.role == "estimator")).one().id
        with self.assertRaises(repository.NotFound):
            with repository.atomic(self.cid):
                repository.create_change("d", "normal", ["x1.png"], submitted_by_user_id=foreign_id)
        with self.assertRaises(repository.NotFound):
            with repository.atomic(self.cid):
                repository.create_change("d", "normal", ["x2.png"], submitted_by_user_id=9999)
        with self.assertRaises(ValueError):
            with repository.atomic(self.cid):
                repository.create_change("d", "normal", ["x3.png"], submitted_by_user_id=estimator)
        self.assertEqual(self.count(Notification), 0)

    # the GC link fixes the company
    def seed_other_company(self):
        with Session(self.engine) as s:
            s.add_all(
                [
                    User(company_id=self.other_id, role="field", name="Other Field"),
                    User(company_id=self.other_id, role="estimator", name="Other Estimator"),
                    User(company_id=self.other_id, role="gc", name="Other GC", email="g@example.com"),
                ]
            )
            s.commit()

    def other_change_token(self):
        self.seed_other_company()
        with repository.atomic(self.other_id):
            change = repository.create_change("Other job", "normal", ["other.png"], "T", "north-park")
            token = repository.send_to_gc(change["id"], None, 50, 1)["token"]
        return change, token

    def test_link_of_another_company_resolves_without_an_explicit_company(self):
        change, token = self.other_change_token()
        mine = self.submit()
        with unittest_env(WORKSPACE_COMPANY_ID=str(self.cid)):
            with repository.atomic():  # default company is the first one
                self.assertEqual(repository.change_for_token(token)["id"], change["id"])
            with repository.atomic():
                self.assertEqual(repository.decide(token, "approved"), {"status": "approved"})
                # later queries in the same transaction use the link's company
                self.assertEqual(repository.work_order("north-park")["revision"], 1)
            with self.assertRaises(repository.Conflict):
                with repository.atomic():
                    repository.decide(token, "approved")
        with repository.atomic(self.other_id):
            self.assertEqual(repository.work_order("north-park")["additional_amount"], 50)
            self.assertEqual(len(repository.list_notifications("contractor")), 1)
        # the first company is untouched
        with repository.atomic(self.cid):
            self.assertEqual(repository.work_order("north-park")["revision"], 0)
            self.assertEqual(repository.get_change(mine["id"])["status"], "submitted")
            self.assertEqual(len(repository.list_changes()), 1)
            self.assertEqual(repository.list_notifications("contractor"), [])

    def test_explicit_company_still_requires_the_link_to_belong_to_it(self):
        _change, token = self.other_change_token()
        with repository.atomic(self.cid):
            self.assertIsNone(repository.change_for_token(token))
        with self.assertRaises(repository.NotFound):
            with repository.atomic(self.cid):
                repository.decide(token, "approved")
        with repository.atomic(self.other_id):
            self.assertIsNotNone(repository.change_for_token(token))
            self.assertEqual(repository.work_order("north-park")["revision"], 0)

    def test_unknown_link_leaves_the_default_company_in_place(self):
        with repository.atomic():
            self.assertIsNone(repository.change_for_token("nothing"))
            self.assertEqual(repository._ctx().company_id, default_company_id())

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


class DatabaseUrlTests(unittest.TestCase):
    def test_postgres_urls_name_the_psycopg_3_driver(self):
        from db.database import normalize_database_url as normalize

        self.assertEqual(normalize("postgres://u:p@h:5432/db"), "postgresql+psycopg://u:p@h:5432/db")
        self.assertEqual(normalize("postgresql://u:p@h/db?sslmode=require"), "postgresql+psycopg://u:p@h/db?sslmode=require")
        self.assertEqual(normalize("postgresql+psycopg://u:p@h/db"), "postgresql+psycopg://u:p@h/db")

    def test_other_urls_are_left_alone(self):
        from db.database import normalize_database_url as normalize

        for url in ("sqlite://", "sqlite:///x.db", "postgresql+psycopg2://u:p@h/db"):
            self.assertEqual(normalize(url), url)


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
