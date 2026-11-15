# Week 1 tasks (Nov 11 to Nov 18, 2026)

Goal: by the partner meeting on **Wed Nov 18**, show the demo running on a real database. Field submits with photos, the estimator adds cost and timeline, the GC decides from an emailed link, everyone is notified, and the fast track works. Sign-in for field, estimator and manager is in scope.

Read [AGENTS.md](../AGENTS.md) first. Each brief gives the owner, due date, what the task depends on, the "done when" line, the files the task may edit, and the spec sections to read. Spec sections are in [SPECIFICATIONS-v0.2.MD](../SPECIFICATIONS-v0.2.MD).

If a dependency is not merged yet, code against the contract or a stub and say so in the PR. Dates are the plan's; if a task will slip, say so in the PR or to the owner by Fri Nov 13.

Order of the main chain: B2 (schema), then B3 (repository layer), then J4 (routes on the database). Sign-in chain: B7, then J5 and U6.

---

## B1 Clean the local `persistentdb` branch

- **Owner:** Bona. **Due:** Thu Nov 12. **Depends on:** nothing.
- **Task:** Discard the broken uncommitted edits in `backend/db/models.py` and pull the Nov 3 schema from `origin/persistentdb`.
- **Done when:** The local branch matches origin and `backend/db/models.py` imports without errors.
- **May edit:** local git state only. No PR.
- **Note for agents:** do not discard anything without Bona confirming. The broken edits were never committed.

## B2 Schema v2 and Supabase migration

- **Owner:** Bona. **Due:** Fri Nov 13. **Depends on:** B1.
- **Task:** Extend the Nov 3 schema: several photos per change, proposed cost and timeline on the revision (money as integer cents plus currency), a priority flag, a company on every tenant-owned record, an approval-link table that stores only the token hash with expiry and revocation, role values field, estimator, manager and GC, and the single status set from AGENTS.md. Write a migration for the Supabase database.
- **Done when:** The tables exist in Supabase and the models match them. After this merges, the schema is frozen for the week except for fixes agreed with Jalen.
- **May edit:** `backend/db/models.py`, `backend/db/migrations/` (new), `backend/db/database.py`.
- **Spec:** Data model and storage; Workflow and approval rules (status set); Personas.
- **Note:** `SQLModel.create_all()` does not alter existing tables, so changes need a migration. Do not run it against Supabase without Bona.

## B3 Repository layer

- **Owner:** Bona. **Due:** Mon Nov 16. **Depends on:** B2 (publish the function signatures and an in-memory version by Fri Nov 13 so Jalen can start).
- **Task:** Add repository functions with the same names and behaviour as the public functions in `backend/services/store.py` (the prototype on `main`), backed by the B2 tables. A setting (for example `WORKSPACE_BACKEND=sqlite|postgres`) chooses the store, so `main` stays demoable until cutover. The repository should create a change, list changes, record the estimator's review, authorize a fast-track change, send to the GC, record the GC's decision, and read and write notifications. Every function takes the company and filters by it. This replaces `backend/services/store.py`.
- **Done when:** Jalen's routes call it and data survives a backend restart.
- **May edit:** `backend/db/repository.py` (new), `backend/db/database.py`.
- **Spec:** Data model and storage; Workflow and approval rules.

## B4 AI cost brief

- **Owner:** Bona. **Due:** Mon Nov 16. **Depends on:** nothing.
- **Task:** Write one page that Con can use to judge feasibility: expected token usage for an estimate, a monthly budget, the model choice, and the two data tiers (minimum proof of concept, full training). Check the Nov 4 price figures against current AWS Bedrock pricing for the chosen model and cite the pages used.
- **Done when:** The page is in `docs/ai-cost-brief.md`, every price has a source, and assumptions are listed.
- **May edit:** `docs/ai-cost-brief.md` (new).
- **Spec:** AI cost estimation.

## B5 Track Tad's data

- **Owner:** Bona. **Due:** Fri Nov 13. **Depends on:** nothing.
- **Task:** Keep a list of what Tad's company has sent and what is missing against the Nov 5 request, and draft a follow-up email for Bona to send if nothing has arrived by Fri Nov 13. Also include the question of who "Zach Smith" is in the Nov 4 notes.
- **Done when:** `docs/data-status.md` lists received and missing items and the follow-up draft. Nothing is sent without Bona.
- **May edit:** `docs/data-status.md` (new). Never commit Tad's company data to the repository.
- **Spec:** AI cost estimation (data from Tad).

## B6 Partner agenda, demo script and board

- **Owner:** Bona. **Due:** Mon Nov 16. **Depends on:** nothing.
- **Task:** Draft the partner meeting agenda and the demo script from the plan's checklist. Keep the plan doc's task table current.
- **Done when:** `docs/demo-script.md` exists and the agenda is ready for Bona to send to the partners.
- **May edit:** `docs/demo-script.md` (new).

## B7 Supabase sign-in setup

- **Owner:** Bona. **Due:** Fri Nov 13. **Depends on:** B2 (role values).
- **Task:** Enable sign-in in the Supabase project, create test accounts for field, estimator and manager, and make sure each user's role is stored on the user record.
- **Done when:** The three test accounts sign in and the role is saved on the user record. Write the setup steps in `docs/auth-setup.md` without any keys or passwords.
- **May edit:** `backend/db/`, `docs/auth-setup.md` (new). Test account passwords go to Jalen and Uriel privately, never in the repository.
- **Spec:** Notifications and GC approval; API and security.

## J1 Several photos per change

- **Owner:** Jalen. **Due:** Fri Nov 13. **Depends on:** nothing (use the current store until B3).
- **Task:** Let the change endpoint accept several photos and return all of their keys.
- **Done when:** Several photos are saved and returned, and tests cover it.
- **May edit:** `backend/api/`, `backend/schemas/`, `backend/services/photos.py`, `backend/tests/`, `docs/openapi.json`.

## J2 Estimator review and manager authorize routes

- **Owner:** Jalen. **Due:** Mon Nov 16. **Depends on:** B2 and B3 signatures.
- **Task:** Add a route where the estimator saves the description, requested timeline and proposed cost, and sends the change on. Add a route where the manager authorizes a high-priority change to start before the estimate.
- **Done when:** The estimator's saved terms appear on the GC link. The manager can authorize a high-priority change before the estimate exists, and the status becomes `authorized_to_proceed`.
- **May edit:** `backend/api/`, `backend/schemas/`, `backend/services/`, `backend/tests/`, `docs/openapi.json`.
- **Spec:** Workflow and approval rules; API and security.

## J3 Emailed GC link

- **Owner:** Jalen. **Due:** Mon Nov 16. **Depends on:** J2.
- **Task:** Send the GC a templated email with the approval link. Keep printing the link to the console as a fallback. Bona sets up the email service; read its key from the backend settings, never from the repository. Also send a heads-up email when the manager authorizes a fast-track change.
- **Done when:** The GC receives a link, the decision is recorded, and the console link still works when no email key is set.
- **May edit:** `backend/services/email.py` (new), `backend/api/`, `backend/core/config.py`, `backend/tests/`.
- **Spec:** Notifications and GC approval.

## J4 Routes on the database

- **Owner:** Jalen. **Due:** Tue Nov 17. **Depends on:** B3.
- **Task:** Move every route from `services/store.py` to the repository layer (B3), switching with the same setting. Update the tests.
- **Done when:** The full workflow passes against the real database and data survives a restart.
- **May edit:** `backend/api/`, `backend/services/`, `backend/tests/`, `docs/openapi.json`.

## J5 Role checks on routes

- **Owner:** Jalen. **Due:** Mon Nov 16. **Depends on:** B7.
- **Task:** Verify the Supabase sign-in token on the backend and enforce the caller's role on each route: field submits, estimator reviews, manager authorizes. The GC link stays token-only. Also add `GET /api/v1/me`, which returns the signed-in user's id, name and role (looked up from the verified token's `sub`, never from the request), so the app can show the right screens (U6). Agree the response shape with Uriel and add it to `docs/openapi.json`.
- **Done when:** A wrong role gets a 403, the GC link still works without an account, and `GET /api/v1/me` returns the caller's id, name and role for a valid token and 401 without one.
- **May edit:** `backend/api/`, `backend/core/`, `backend/tests/`.
- **Spec:** API and security.

## U1 Rename the roles in the UI

- **Owner:** Uriel. **Due:** Thu Nov 12. **Depends on:** nothing.
- **Task:** Replace the role names in the screens and text with field, estimator, manager and GC.
- **Done when:** No "client" wording is left on screen.
- **May edit:** `frontend/`.
- **Spec:** Personas.

## U2 Several photos on the capture screen

- **Owner:** Uriel. **Due:** Fri Nov 13. **Depends on:** J1 (use the contract in `docs/openapi.json`).
- **Task:** Let the field user attach several photos, with a short prompt about what to photograph.
- **Done when:** A field user attaches several photos from a phone.
- **May edit:** `frontend/`.

## U3 Estimator and manager screens

- **Owner:** Uriel. **Due:** Mon Nov 16. **Depends on:** J2 contract.
- **Task:** Build the estimator review screen (cost, timeline) and the manager's authorize-now action for high-priority changes.
- **Done when:** An estimator completes a review and a manager authorizes a fast-track change in the app.
- **May edit:** `frontend/`.
- **Spec:** Workflow and approval rules.

## U4 GC approval page

- **Owner:** Uriel. **Due:** Mon Nov 16. **Depends on:** the approval-session routes (they exist today).
- **Task:** Build the web page the GC opens from the emailed link. Opening it must not decide anything; only an explicit button press does.
- **Done when:** A GC approves or declines without an account.
- **May edit:** `frontend/`.
- **Spec:** Notifications and GC approval.

## U5 Review Spec v0.2

- **Owner:** Uriel. **Due:** Thu Nov 12. **Depends on:** nothing.
- **Task:** Review `SPECIFICATIONS-v0.2.MD`, correct anything wrong, and sign off the personas.
- **Done when:** Comments are resolved and the personas are agreed.
- **May edit:** `SPECIFICATIONS-v0.2.MD`.

## U6 Login and role-based navigation

- **Owner:** Uriel. **Due:** Mon Nov 16. **Depends on:** B7.
- **Task:** Add a login screen using Supabase sign-in and show each role only its own screens.
- **Done when:** Each role signs in and sees only its own screens.
- **May edit:** `frontend/`. Supabase public settings go in `frontend/.env`, which is never committed.

## A1 Demo dry run

- **Owner:** all three. **Due:** Tue Nov 17. **Depends on:** everything above.
- **Task:** Run the demo script on a phone in Expo Go, twice, from start to finish, and list what breaks.
- **Done when:** The script runs start to finish twice. Open a small PR per fix, owned by the area's owner.
