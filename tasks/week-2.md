# Week 2 tasks (Nov 23 to Dec 1, 2026)

Goal: reach the spec's Phase 2 gate. The estimator sees an AI scope-and-cost suggestion on sample change orders from Tad's data and rates it. In the same stretch, move the demo from "works on the club's Wi-Fi" toward something a partner can open from anywhere: ready to host over HTTPS, photos kept private, and a GC link whose token does not stay in the address bar.

Con's framing from the Nov 19 meeting: the semester goal is to show the change order flow works end to end and that the AI gives believable estimates. It is not a finished product. The AI work comes first; hosting, private photos and the GC token are real hardening and follow it.

What Tad's replies (Nov 18 and 19) changed:

- **No labor and materials split exists.** Tad bills and prices change orders as lump sums, so the AI suggests a lump-sum range and nothing finer. Do not plan around a breakdown.
- **The "extra" contract totals are explained.** Three proposals were revised after the original, and one large change was agreed by email and phone with no separate change order form. So the original proposal is the scope baseline, and the revisions are extra examples of a scope change and its price.
- **Approvals are mostly informal.** Where Tad found approval dates, only some were written; others were phone, text or the GC's own portal, and work was sometimes requested before a change order went out. That is the gap the emailed GC link and the fast track address.
- **More records may follow.** Tad is checking for declined or reduced change orders, and some change orders on one project are still waiting for the GC. The set of records may grow, so fix the held-out split before any run.

Read [AGENTS.md](../AGENTS.md) first. Each brief gives the owner, due date, what the task depends on, the "done when" line, the files the task may edit, and the spec sections to read. Spec sections are in [SPECIFICATIONS-v0.2.MD](../SPECIFICATIONS-v0.2.MD).

Dates are the plan's. **Wed Nov 25** is the last working day before Thanksgiving; there is no work expected Thu Nov 26 to Sun Nov 29. **Tue Dec 1** is the end of the week and the target for anything marked "after Thanksgiving". Bona schedules the next meeting with Con and Tad for the week of Nov 30; the work should be demo-ready by then. If a task will slip, say so in the PR or to the owner by Tue Nov 24.

If a dependency is not merged yet, code against the contract or a stub and say so in the PR.

**Hosting is on hold (decided Nov 23).** Bona will not create the Render account until the next meeting with Con, to ask the partners to pay for it. The decision is made and merged (`docs/hosting.md`), but J11, U11 and A2 cannot finish this week. Until then the demo runs from the local network, and the Supabase database stays live on its Free plan, which Bona keeps active and checks before any demo. Everything else in this plan is unaffected.

Order of the main chains:

- AI: B8 (data and AWS), then B9 (suggestion worker), then J7 (suggestion routes) and U7 (suggestion panel), then B10 (evaluation).
- GC link: J8 (token exchange), then U8 (GC page).
- Photos: B11 (decision), then J9 (private storage), then U9 (show photos).
- Hosting (on hold until after the meeting with Con): B12 (decision, done), then J11 (API) and U11 (web build), then A2.

## Rules for this week

- **Tad's data never enters the repository.** Not the files, excerpts, names or amounts, and not in PRs, issues or chat summaries. It lives in a private location outside the repo and stays on US servers. Results are reported as ranges and counts only. Anything about the NDA goes to Bona.
- **Keys and secrets** live in each person's local `.env` and in the host's secret settings. The Supabase service-role key and AWS credentials are backend-only and are never put in a variable that starts with `EXPO_PUBLIC_`.
- **AI is advisory.** It suggests scope and cost with a reason and a confidence; the estimator decides. It never approves anything and it does not receive photos.
- **The fast-track rule is not yet confirmed by Con.** Do not change it. It is on the agenda for the next meeting. Tad's approval dates show work being requested before a change order was sent, which is evidence for the rule, not confirmation of it.
- **Say what the data is not.** It has no labor and materials breakdown, the approval evidence is partial, and everything we have was billed at the approved lump sum. Reports must say so.

---

## B8 Data and AWS setup for the AI

- **Owner:** Bona. **Due:** Mon Nov 23. **Depends on:** nothing.
- **Task:** Put Tad's proposals, change orders and invoices in a private US-only S3 bucket, outside the repository. Include the new documents from his Nov 18 reply (revised proposals for three projects, the email that serves as one project's change order, and a GC schedule of values); they are attachments in Bona's SDSU inbox and are not yet in the shared folder. Confirm Amazon Bedrock model access for Claude Sonnet 5.5 and Claude Haiku 5.5 in a US region, and set an AWS budget alert for the $100 credit. Choose the held-out set: Con advised holding back 3 to 4 records to validate accuracy, so with five change orders, hold back three and use two as examples. Fix the split before the worker runs and do not change it after seeing results, because Tad may send more records. Re-check the Bedrock prices in the cost brief and note the date.
- **Done when:** The data is in the bucket and nowhere in the repo, model access works from a test call, the budget alert exists, the new documents are in the bucket, and the split is written down without any content from the documents.
- **May edit:** `docs/ai-cost-brief.md`. Everything else for this task is outside the repository.
- **Spec:** AI cost estimation.

## B9 Suggestion worker

- **Owner:** Bona. **Due:** Tue Nov 24. **Depends on:** B8.
- **Task:** Add a worker that takes a change order and the matching original proposal and returns a scope flag, a suggested cost range, a reason and a confidence. Start without a knowledge base: pass the matching proposal and the two example change orders with their billed amounts straight to the model, and add a knowledge base later when there is more data. Use a US region only. Extend `ai_suggestion` with a cost range, a prompt version and the estimator's response (accepted, edited or dismissed, plus a rating) in a migration. Photos are not an input. The suggested cost is a lump-sum range, because there is no labor and materials breakdown. Compare against the original proposal, not a revised one, since a revision may already include the change.
- **Done when:** A suggestion is produced for each held-out change order and stored with model id, prompt version, reason and confidence, and nothing from the documents is logged or committed.
- **May edit:** `backend/ai/`, `backend/db/models.py`, `backend/db/migrations/` (new), `backend/db/repository.py`.
- **Spec:** AI cost estimation; Data model and storage.
- **Note:** only Bona's agents change the models and migrations. Tell Jalen the new fields and the function signatures by Mon Nov 23 so J7 can start.

## B10 Evaluation on held-out change orders

- **Owner:** Bona. **Due:** Wed Nov 25. **Depends on:** B9.
- **Task:** Run B9 on the three held-out change orders. Compare the scope flag with the reason each change was needed, and the cost range with the billed amount. Try both Sonnet 5.5 and Haiku 5.5 and note the cost per run. Add the contract revisions as extra cases of a scope change and its price, kept apart from the held-out set. Do not use approval dates as ground truth; they are partial. Replace the cost brief's assumed token counts with measured ones.
- **Done when:** `docs/ai-poc-results.md` reports counts, ranges and costs only, with the limits stated: three held-out cases, all billed at the approved lump sum, no labor and materials breakdown and only partial approval evidence, so this shows judgment and not accuracy.
- **May edit:** `docs/ai-poc-results.md` (new), `docs/ai-cost-brief.md`.
- **Spec:** AI cost estimation.

## B11 Photo storage decision

- **Owner:** Bona. **Due:** Mon Nov 23. **Depends on:** nothing.
- **Task:** Decide where photos live: a private Supabase Storage bucket in the existing project (recommended) or a private S3 bucket. The `photo` table already stores a `storage_key`, not a public URL, so a migration may not be needed. Decide how photos are served: short-lived signed links or through the API.
- **Done when:** The decision and its reason are in `docs/photo-storage.md`, the bucket exists and is private, and any migration is merged.
- **May edit:** `docs/photo-storage.md` (new), `backend/db/` if a migration is needed.
- **Spec:** Data model and storage; API and security (private evidence).
- **Status (Nov 23):** the decision is merged (`docs/photo-storage.md`). Creating the private bucket and sharing the secret key with Jalen are Bona's manual steps and are still to do.

## B12 Hosting decision

- **Owner:** Bona. **Due:** Mon Nov 23. **Depends on:** nothing.
- **Task:** Choose a host for the API and one for the web build, using free or low-cost tiers in a US region. Compare cold starts, since a sleeping free tier can fail during a demo. Decide where the secrets live and who holds the accounts.
- **Done when:** `docs/hosting.md` names the providers, the cost, the secret settings each needs, and who holds the accounts. No keys appear in it.
- **May edit:** `docs/hosting.md` (new).
- **Spec:** Notifications and GC approval (reachable HTTPS); API and security.
- **Status (Nov 23):** the decision is merged (`docs/hosting.md`: Render for the API, Cloudflare Pages for the web build). Creating the accounts and paying is on hold until the next meeting with Con. The Supabase Free plan can pause an idle project, so Bona keeps it active and checks it before any demo.

## B13 Tad follow-up and next semester

- **Owner:** Bona. **Due:** Tue Dec 1. **Depends on:** nothing.
- **Task:** Thank Tad for the Nov 18 and 19 replies. Ask only for what he can provide: any declined or reduced change orders he can share (he is checking), the change orders on one project that the GC has not yet approved, a key that maps his change order letters to the documents we hold (his letters run past the five projects), and confirmation of the approval for the project where the GC's reply "reads as a yes". Drop the request for a labor and materials split, which he cannot provide. Invite Tad to see the new demo, since he missed the meeting. Write a one-page note with two or three productization options (a SaaS product, or embedded in a company's own system), as Con suggested, and use the finding that most approvals are informal as one argument for the emailed link. Set up a conversation with Adi about continuing next semester. Nothing is sent without Bona.
- **Done when:** The reply is sent, `docs/data-status.md` is updated with the new statuses (rows for labor and materials marked not available), `docs/productization-options.md` exists, and the meeting with Adi is requested.
- **May edit:** `docs/productization-options.md` (new), `docs/data-status.md` (statuses only).
- **Spec:** AI cost estimation (data from Tad).

---

## J6 Clock tolerance for token checks

- **Owner:** Jalen. **Due:** Mon Nov 23. **Depends on:** nothing.
- **Task:** Review and merge the branch `fix-token-clock-leeway`, which lets the token check tolerate up to 30 seconds of clock difference. Without it, a server clock a second or two behind Supabase refuses every fresh token and every sign-in fails with a 401.
- **Done when:** The change is merged, the full workflow passes, and a token issued a few seconds in the future is accepted while one far in the future is not.
- **May edit:** `backend/core/auth.py`, `backend/tests/`.
- **Spec:** API and security.

## J7 Suggestion routes

- **Owner:** Jalen. **Due:** Wed Nov 25. **Depends on:** B9 signatures (Mon Nov 23).
- **Task:** Update `POST /changes/{id}/suggestion` to call the worker, return the stored suggestion, and add routes to list a change's suggestions and to save the estimator's response and rating. Stop sending photos to the model. Only the estimator may ask for or rate a suggestion. Add the routes to `docs/openapi.json`.
- **Done when:** An estimator can request, read and rate a suggestion through the API, other roles get a 403, no photo reaches the AI call, and tests cover it.
- **May edit:** `backend/api/`, `backend/schemas/`, `backend/services/`, `backend/tests/`, `docs/openapi.json`.
- **Spec:** AI cost estimation; API and security.

## J8 GC link token exchange, expiry and revocation

- **Owner:** Jalen. **Due:** Wed Nov 25. **Depends on:** nothing.
- **Task:** When the GC opens the link, exchange the long token in the address for a short-lived session so the token does not stay in the URL, browser history or logs. Enforce link expiry and revocation, which `approval_link` already stores. Make approve and decline accept an idempotency key so a retry never records a second decision. Opening or reloading must still decide nothing, and a decided proposal still offers no buttons.
- **Done when:** The page works from the new session, an expired or revoked link is refused, a repeated decision is recorded once, and tests cover each case.
- **May edit:** `backend/api/`, `backend/schemas/`, `backend/services/`, `backend/tests/`, `docs/openapi.json`.
- **Spec:** Notifications and GC approval; API and security.

## J9 Private photo storage

- **Owner:** Jalen. **Due:** Tue Dec 1. **Depends on:** B11.
- **Task:** Save photos to the private bucket from B11, store only the key in `photo.storage_key`, and serve them with short-lived signed links or through the API. Stop serving photos from the public `uploads` folder. The storage credential is backend-only.
- **Done when:** A photo uploaded by a field user shows for the estimator from any PC, a direct public URL is refused, and tests cover upload and access by role.
- **May edit:** `backend/api/`, `backend/services/photos.py`, `backend/core/config.py`, `backend/tests/`, `docs/openapi.json`.
- **Spec:** Data model and storage; API and security (private evidence).

## J10 Scope lists and notifications by role

- **Owner:** Jalen. **Due:** Tue Dec 1. **Depends on:** nothing.
- **Task:** Make the change list and notifications depend on who is signed in, not on a role the app names. Retire the legacy `admin-approve` route. Replace the single `GC_EMAIL` setting with the GC contact of the change's company.
- **Done when:** A field user sees only their own changes, notifications go to the right people, `admin-approve` is gone, and the GC link goes to the company's GC.
- **May edit:** `backend/api/`, `backend/schemas/`, `backend/services/`, `backend/tests/`, `backend/core/config.py`, `docs/openapi.json`. A data change goes through Bona.
- **Spec:** Notifications and GC approval; API and security.

## J11 Host the API

- **Owner:** Jalen. **Due:** after the Render account exists (on hold until after the meeting with Con; was Tue Dec 1). **Depends on:** B12 and the account.
- **Task:** Deploy the API to the host chosen in B12 with its secrets in the host's secret settings. Set `APP_URL` and CORS for the hosted web build, and add a health check.
- **Done when:** The hosted API answers `/health`, signs in the three test accounts, and the GC link opens over HTTPS from a phone off the club's Wi-Fi.
- **May edit:** `backend/` configuration and deploy files, `backend/core/config.py`, `docs/hosting.md`.
- **Spec:** Notifications and GC approval; API and security.
- **Until the account exists:** prepare what needs no account: the start command, the settings list from `docs/hosting.md`, and, if you want one, a small separate keep-alive that touches the database now and then so an idle Free project does not pause (keep `/health` itself independent of the database). Do not deploy.

---

## U7 Estimator suggestion panel

- **Owner:** Uriel. **Due:** Wed Nov 25. **Depends on:** J7 contract.
- **Task:** On the estimator's review screen, show the AI's scope flag, cost range, reason and confidence, clearly labelled as a suggestion. Let the estimator accept, edit or dismiss it and rate it. Never fill the estimator's cost without the estimator choosing to.
- **Done when:** An estimator requests a suggestion, reads it, applies or dismisses it, and rates it in the app.
- **May edit:** `frontend/`.
- **Spec:** AI cost estimation; Workflow and approval rules.

## U8 GC page wording and token exchange

- **Owner:** Uriel. **Due:** Wed Nov 25. **Depends on:** J8 contract.
- **Task:** Con's feedback: the page should say plainly what was requested, the cost and the timeline, in the spirit of "you asked us to change this, here is what it costs". Rewrite the page's copy, and use the exchanged session from J8 so the token is not left in the address. Opening still decides nothing; only the confirmation does.
- **Done when:** A GC reads what was requested, the cost in dollars and the calendar days, approves or declines, and the token is gone from the address after opening.
- **May edit:** `frontend/`.
- **Spec:** Notifications and GC approval.

## U9 Photos from private storage

- **Owner:** Uriel. **Due:** Tue Dec 1. **Depends on:** J9 contract.
- **Task:** Load photos from the signed links or API routes that J9 provides, with a sensible placeholder while they load or when a link has expired.
- **Done when:** Photos show on the capture confirmation, the estimator's review and the change detail from any PC.
- **May edit:** `frontend/`.
- **Spec:** Data model and storage.

## U10 Persistent session

- **Owner:** Uriel. **Due:** Tue Dec 1. **Depends on:** nothing.
- **Task:** Keep staff signed in across a reload and refresh the token before it expires. Store the session in secure storage on the phone, never in a place other apps or pages can read. Sign out removes it. Signing in still derives the role from `/api/v1/me`.
- **Done when:** Closing and reopening the app keeps the user signed in, an hour of use does not sign them out, and a 401 still returns to login.
- **May edit:** `frontend/`.
- **Spec:** API and security.

## U11 Host the web build

- **Owner:** Uriel. **Due:** after J11 is live (on hold until after the meeting with Con; was Tue Dec 1). **Depends on:** B12 and J11.
- **Task:** Publish the web build, including the GC page, to the host chosen in B12 with the public API address and Supabase public settings. Only public settings go in the build.
- **Done when:** The web build loads over HTTPS from a phone off the club's Wi-Fi and signs in against the hosted API.
- **May edit:** `frontend/`, `docs/hosting.md`.
- **Spec:** Notifications and GC approval.
- **Until the API is hosted:** the web build needs the hosted API's address, so do not deploy. You can still check the export builds (`npx expo export --platform web`), and that `/approve?token=...` resolves to the right page in the static export, so the first deploy has no surprises.

## U12 Run the browser tests in CI

- **Owner:** Uriel. **Due:** Tue Dec 1. **Depends on:** nothing.
- **Task:** Run the Playwright tests for the login flow in the GitHub check, so a change that breaks sign-in fails the PR.
- **Done when:** The check runs the browser tests, passes on `main`, and fails when a login test is broken on purpose.
- **May edit:** `frontend/`, `.github/workflows/ci.yml` (the frontend job only).
- **Spec:** API and security.

## U13 Update the specification

- **Owner:** Uriel. **Due:** Wed Nov 25. **Depends on:** nothing.
- **Task:** Bring `SPECIFICATIONS-v0.2.MD` up to date: the implementation snapshot, the "Zack" spelling, the decisions from the Nov 19 meeting, and the open items. The fast-track rule stays marked as unconfirmed.
- **Done when:** The snapshot matches `main` and no open PR is described as shipped.
- **May edit:** `SPECIFICATIONS-v0.2.MD`.
- **Spec:** all sections.

---

## A2 Hosted integration check

- **Owner:** all three. **Due:** after hosting is live (was Tue Dec 1). Until then run the same check on the local network. **Depends on:** J8, J9, U8, U9, and J11 and U11 for the hosted run.
- **Task:** On a phone off the club's Wi-Fi, run the demo against the hosted app: field submits with photos, the estimator requests and rates an AI suggestion, the GC decides from the emailed link, and the three roles see the result. List what breaks.
- **Done when:** The flow runs start to finish on the hosted app, photos load from private storage, and the GC link token is not left in the address. Open a small PR per fix, owned by the area's owner.
