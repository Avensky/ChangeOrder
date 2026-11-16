# Demo script and partner agenda: Wed Nov 18, 2026

Task B6. Owner: Bona. First written Nov 11; updated Nov 15 after Uriel's review of PR #16 and after merging `main`; updated Nov 16 after the first live phone run on Supabase.

This file has two parts:

1. [The demo script](#part-1-demo-script), with a pre-demo checklist for Mon Nov 16, Tue Nov 17 and Wed Nov 18.
2. [The partner meeting agenda](#part-2-partner-meeting-agenda-draft), as a draft email for Bona to send.

Button labels in the script are the ones in `frontend/src` on `main` as of Nov 15. Correct any that differ at the dry run (A1).

**Rule for what we say out loud:** every claim about the live database, sign-in, notifications and delivered email is gated on the Tue Nov 17 dry run. If a line was not seen working then, we do not claim it on Wednesday.

---

## Part 1: Demo script

**The one point to land:** a change reported from a phone is saved, priced by the estimator, and decided by the GC from a link, with no GC account.

**Length:** about 14 minutes for the six steps (2 + 1.5 + 2 + 3 + 1.5 + 3.5 = 13.5). The agenda gives the demo 12 minutes; if the dry run runs long, shorten step 6 to the manager's authorize and the GC's decision only.

### Open decisions (pending Bona)

| Decision | Path A | Path B | Default |
| --- | --- | --- | --- |
| **Email** (pending Bona) | Real email is configured and a test link reaches the test GC inbox in the dry run: send the real email. | No email provider: the link is copied from the backend console, and we show the email template instead (the wording from `backend/services/email.py`). | **B** until real email is configured and delivered in the dry run |
| **Sign-in go/no-go, Tue Nov 17 midday** (pending Bona) | All three accounts (field, estimator, manager) pass on the live database **and** in Expo Go: demo with login. | Any account fails: demo the role-picker build on the SQLite store and present sign-in as the next step. | **Decide at midday Tue.** Mon Nov 16: all three accounts signed in on a phone against Supabase and the full workflow ran, so the default is **A**. Re-confirm Tuesday on the demo network. Keep B as the fallback |

Both paths are written into each step below. In the role-picker build, the role picker in the app is a preview, not authentication, and we say so.

**Path B needs the SQLite store.** With `WORKSPACE_BACKEND=postgres` every staff request needs a sign-in token, so the role picker alone shows "Sign in first". For Path B, leave `WORKSPACE_BACKEND` unset in `backend/.env` and restart the backend.

### What is built, and what is still open (as of Nov 16)

| Piece | State on `main` | Notes for the demo |
| --- | --- | --- |
| Several photos per change | Merged | Show three photos in step 1 |
| Persistence on SQLite | Merged | A restart on SQLite works. **It does not prove Supabase** |
| Estimator review (cost, timeline) and manager authorization | Merged | Steps 3 and 6 |
| GC review page and the decision confirmation | Merged | Step 4 |
| GC link, console fallback | Merged | Copied from the backend console |
| Email to the GC | Code merged; **provider not configured** (needs `EMAIL_API_KEY`, `EMAIL_API_URL`, `EMAIL_FROM`, `GC_EMAIL`) | Console link unless the dry run proves delivery |
| Persistence on Supabase (B2, B3, J4) | Merged. Restart check passed on `main` (Jalen, Nov 16) | Chosen with `WORKSPACE_BACKEND=postgres`. Re-run at the dry run; see the restart checkbox below |
| Staff sign-in, backend (B7, J5) | Merged (#23). Role checks on every staff route | The server needs `SUPABASE_URL` in `backend/.env` |
| Staff sign-in, app (U6, PR #24) | **Open PR.** All three accounts passed on a phone on Nov 16 with `main` merged in locally | Merge #24 (with `main` merged in) before the dry run. Sessions are memory-only |
| Field user sees their own submissions (PR #30) | **Open PR** | Without it a signed-in field user's list stays empty in step 1 |
| GC page crash with the NativeWind color-scheme error (PR #29) | **Open PR** | Without it the GC page fails in step 4 on the web build |
| In-app alerts, push, SMS | Alerts are stored in the app. **No email-to-field, SMS or phone push exists** | Do not promise any of them |

**Supabase restart result, to fill in at the dry run:**

- [ ] Backend started with `WORKSPACE_BACKEND=postgres`. Result: seen working Nov 16 (Jalen, on `main` `42a8f25`, and Bona on a phone). Re-run at the dry run: ____________
- [ ] A change submitted, backend stopped and restarted, the same change (with its photos) still listed. Result: seen working Nov 16 (Jalen: change, terms and GC link all survived the restart). Re-run at the dry run: ____________
- [ ] If either box is not ticked by Tue Nov 17 evening, step 2 runs on SQLite and we say "saved on the demo store; the Supabase database is next". We do not say "Supabase".

### People and devices (proposed, Bona to confirm)

| Who | Does what |
| --- | --- |
| Bona | Narrates and runs the agenda |
| Uriel | Holds the phone: plays the field user |
| Jalen | Runs the demo PC: backend terminal, estimator, manager, and the GC's inbox or console link |

| Device | Used for |
| --- | --- |
| Phone with Expo Go | Field user (steps 1, 2, 5, 6) |
| Demo PC, terminal 1 | Backend: `npm run dev:backend` |
| Demo PC, terminal 2 | Expo: `npm run dev:frontend` |
| Demo PC, browser window A | Web preview at `http://localhost:8081`, estimator |
| Demo PC, browser window B (second browser or profile) | Web preview, manager |
| **Phone browser, private tab** | The GC link, opened with no staff session (step 4) |
| A team inbox that plays the GC | Only if real email is configured. Never use a real GC's address |

Run the backend and Expo in **two terminals**, not `npm run dev`: `npm run dev` stops both when either stops, and step 2 stops only the backend.

### Step 1: Field reports a change

*About 2 minutes.*

| | |
| --- | --- |
| **Who acts** | Field (Uriel, on the phone) |
| **Tap** | **Path A (sign-in):** sign in as the field test account. **Path B (role picker):** pick the field role in the role picker. Start a new change. Take or pick three photos. Enter a title and description. Choose priority Normal. Submit. |
| **Say** | "A foreman sees something that is not in the contract. They take a few photos, say what it is and how urgent it is, and send it. The photos are for the people reviewing it; the AI does not read them." Path B only: "Sign-in is the next step. This role picker is a preview, not a login." |
| **Audience sees** | Three photo thumbnails on the form, then the new change at the top of the field user's list with status `submitted`. |
| **Fallback** | **Phone cannot reach the backend:** open `http://<PC IP>:8000/health` in Safari on the phone. If that fails, check the PC IP in `frontend/.env` and the network (README, step 4). If it still fails, do this step in the web preview at `http://localhost:8081` on the demo PC, with sample photos saved on the PC. **Camera fails or is slow:** pick the sample photos from the phone's library. |

Sample text: "Owner asked to move the hose bib from the north wall to the east wall. Not in the original proposal."

### Step 2: Restart the backend

*About 1.5 minutes. This is the point of the week. Which store it runs on depends on the Supabase checkbox above.*

| | |
| --- | --- |
| **Who acts** | Jalen on the demo PC, then the field user on the phone |
| **Tap** | In terminal 1 press Ctrl+C. Wait for it to stop. Run `npm run dev:backend` again and wait for "Application startup complete". On the phone, reload the list of changes. |
| **Say** | If the Supabase box is ticked: "Restart the server and the change is still there, because it is saved in the database." If not: "It is now saved to disk instead of the server's memory, so a restart keeps it. The Supabase database is the next step." |
| **Audience sees** | The backend stopping and starting. Then the same change, with its photos and status `submitted`, still in the list. |
| **Fallback** | **Backend does not come back:** read the error in terminal 1, start it once more. **Phone shows an empty list or error:** open the list in the web preview. **Staff must sign in again after a full reload** (Path A): see step 5. **The record is really gone:** say so plainly and move on. Do not work around it. |

Do not save any file under `backend/` during the demo. The backend runs with auto-reload and restarts on every save.

### Step 3: Estimator prices it

*About 2 minutes.*

| | |
| --- | --- |
| **Who acts** | Estimator (Jalen, browser window A) |
| **Tap** | **Path A:** signed in as the estimator. **Path B:** pick the estimator role. Open the submitted change. Look at the photos. Enter the proposed cost and the timeline in **calendar days**. Tap **Send estimate to GC**. |
| **Say** | "The estimator checks whether this is in scope, writes up the change, and sets the price and the time. The estimator decides the number. Later the AI will suggest one, but it never approves anything." |
| **Audience sees** | The estimator's screen with the field photos and description, cost and timeline filled in, then status `awaiting_gc`. After a reload, the field user's copy shows `awaiting_gc`. |
| **Fallback** | **Web preview fails:** use the estimator role on the phone. **Screen fails entirely:** call the estimator route from `http://localhost:8000/docs`; once role checks (J5) are on, that page needs a sign-in token, so rehearse it or drop it. |

Sample values: timeline **2 calendar days**, cost $850.00.

### Step 4: GC decides from the link

*About 3 minutes. The GC opens the link with no account. Opening it must not decide anything.*

**Setup for the phone check (do on Monday, repeat Tuesday).** A native Expo Go QR link is **not** the GC review address. The GC page is the web build:

1. Backend `.env`: `APP_URL=http://<PC-LAN-IP>:8081` (the frontend's reachable address and port). Add `http://<PC-LAN-IP>:8081` to `CORS_ORIGINS`. Restart the backend, then generate a **new** link: old links keep the old address.
2. Frontend `.env`: `EXPO_PUBLIC_API_URL=http://<PC-LAN-IP>:8000` (the backend's address and port).
3. The web build is already served on port 8081 by terminal 2 (`npm run dev:frontend` starts Expo with `--lan`). Do not also run `npm run web`: a second Expo asks for another port. See `frontend/GC-REVIEW.md`.
4. A link beginning with `localhost` points at the phone itself. Regenerate it with the right `APP_URL`.
5. **Off the local network this demo needs hosting** (HTTPS frontend and HTTPS API). A LAN address only works for devices on the same network.

| | |
| --- | --- |
| **Who acts** | GC (Jalen, on the phone browser) |
| **Tap** | Get the link: **email path** (real email configured): open the email in the test inbox and tap the link on the phone. **Console path** (default): copy the link from terminal 1 and open it in a **private tab** in the phone's browser, with no staff session. **Stop. Do not press anything.** Reload the page: the status must be unchanged. Tap **Approve change**. A confirmation opens. Tap **Keep reviewing**: the status must still be unchanged. Tap **Approve change** again, then **Confirm approval**. |
| **Say** | "The general contractor does not have our app and will never sign in. The link shows them the exact proposal: description, photos, cost and calendar days. Opening it decides nothing, so a mail scanner or a stray click cannot approve a change. Even the button only opens a question; only the confirmation decides." |
| **Audience sees** | The GC page with the description, photos, cost and "additional calendar days", and two buttons, **Approve change** and **Decline change**. No sign-in screen. Status still `awaiting_gc` after opening, after reloading, and after **Keep reviewing**. Status `approved` only after **Confirm approval**. |
| **Fallback** | **Email not configured or not arriving in about 20 seconds:** use the console link and show the email template on the PC. **Do not show the raw token:** while sharing the screen, copy the link and paste it straight into the phone; keep terminal 1 off the shared screen or cropped when the link prints. Never paste a link into slides, chat or a PR. **Link opens on `localhost` or fails on the phone:** `APP_URL` is wrong; fix it, restart the backend, and send a new proposal. **Phone cannot reach the backend:** open the link in a browser on the demo PC instead. **GC page fails:** show the proposal from `http://localhost:8000/docs` and say the page is next. |

**Anonymous phone-browser check (must pass on Tuesday):**

- [ ] The link opens in a private phone-browser tab with no staff session and shows the proposal.
- [ ] Reload leaves the status unchanged.
- [ ] **Approve change**, then **Keep reviewing**: status unchanged.
- [ ] **Approve change**, then **Confirm approval**: one saved decision; the field user sees `approved`.
- [ ] On a separate proposal: **Decline change**, then **Confirm decline**: one saved decision.
- [ ] An already-decided link shows no decision buttons.

Do not tell the audience an email was sent unless the dry run showed one delivered. There is no SMS and no phone push.

### Step 5: Field and manager see the result

*About 1.5 minutes.*

| | |
| --- | --- |
| **Who acts** | Field (phone) and manager (browser window B) |
| **Tap** | On the phone, reload the list and open the change. In window B, open the manager's list and the same change. |
| **Say** | "The foreman can see on site that the work is approved. The manager sees it in the office." |
| **Audience sees** | Status `approved` on the phone and on the manager's screen, and an in-app alert for each. |
| **Fallback** | **Status does not update:** pull to refresh or switch tab, then open the change again. **Path A, staff are signed out after a full reload:** staff sessions are memory-only (PR #24), so closing Expo Go or reloading the tab signs the person out. Sign in again with the test account. **Do not promise sessions persist.** Have the test accounts ready in a password manager, off the shared screen. **Alerts not shown:** show the status on the change and say alerts are next. |

**Rehearse account re-entry** (Tuesday): fully close Expo Go, reopen it, and sign in as each of the three accounts in under 30 seconds. Do the same by reloading each browser window. In Path B, there is nothing to re-enter: re-pick the role.

### Step 6: Fast track for a high-priority change

*About 3.5 minutes.*

| | |
| --- | --- |
| **Who acts** | Field (phone), then manager (window B), then estimator (window A), then GC (phone browser) |
| **Tap** | **Field:** new change, two photos, description, priority High, submit. **Manager:** open it, tap **Authorize work now**. **Field:** reload and show the new status. **Estimator:** open it, add cost and calendar days, tap **Send estimate to GC**. **GC:** open the new link in a private phone tab, tap **Approve change** (or **Decline change**), then **Confirm approval** (or **Confirm decline**). Show **Keep reviewing** once. **Field and manager:** reload. |
| **Say** | "Some changes cannot wait for an estimate. For a high-priority change the manager authorizes the work to start now. The estimate follows, and the GC still approves or declines the cost. Nothing is ever approved by a timeout. Con, this is the rule we would like you to confirm today." |
| **Audience sees** | Status `submitted`, then `authorized_to_proceed` right after **Authorize work now**, with no cost yet. After the estimator sends it: `awaiting_gc`. After the GC's confirmation: `approved` (or `declined`) on the phone and the manager's screen. |
| **Fallback** | **Heads-up email to the GC:** say it only if the dry run showed it delivered; otherwise say it is part of the finished version. **Authorize fails in the app:** call the manager route from the API page (same token caveat as step 3). **Short on time:** skip this step and explain the rule from the spec diagram. |

Sample text: "Supply line is leaking behind the wall in unit 204. Drywall closes tomorrow morning, so the repair has to start today." Sample values: timeline **1 calendar day**, cost $2,400.00.

### If the live demo cannot run at all

Play the screen recording made at Tuesday's second dry run and narrate over it. Say that it is a recording.

### Pre-demo checklist

Physical-device and network checks stay **pending** (unticked) until someone has actually run them. Write the date and result next to each tick.

#### Monday Nov 16: setup

- [ ] **Expo and Expo Go versions.** The project is on Expo **SDK 58** (PR #25, merged), and the iPhone has the **current iOS Expo Go** from the App Store, which supports SDK 58. If the app opens with an "incompatible SDK" message, update Expo Go first. Seen working on Bona's phone Nov 16. (Uriel)
- [ ] **Open PRs merged into `main`, in this order:** #29 (GC page color-scheme crash) and #30 (field user sees own submissions), then #24 (login) with `main` merged into it. Without #29 the GC page fails in step 4; without #30 the field list is empty in step 1. Pending. (Uriel for #29 and #24, Bona for #30; Jalen reviews #30)
- [ ] **Sign-in settings.** `backend/.env` has `SUPABASE_URL=https://<project>.supabase.co` (public; without it the app says "sign-in is not configured on the server"). `frontend/.env` has `EXPO_PUBLIC_SUPABASE_URL` (the same https address) and `EXPO_PUBLIC_SUPABASE_ANON_KEY` (the publishable key). The database connection string (`DATABASE_URL`) goes only in `backend/.env`: anything named `EXPO_PUBLIC_` is bundled into the app and served to every device. Restart Expo with `--clear` after changing `frontend/.env`. Pending. (Bona, Uriel)
- [ ] **Backend running.** `npm run dev:backend` starts with no errors and `http://localhost:8000/health` returns `{"status":"ok"}`. Pending. (Jalen)
- [ ] **Store.** Path A runs on `WORKSPACE_BACKEND=postgres` with `DATABASE_URL` in `backend/.env`; path B runs with `WORKSPACE_BACKEND` unset (SQLite). Record the result in the Supabase restart box above. Postgres seen working Nov 16 (Jalen, Bona). (Bona)
- [ ] **Demo network chosen and tested.** Put the PC and phone on it and open `http://<PC IP>:8000/health` in Safari on the phone. Some campus and guest networks block device-to-device traffic; if so, use a phone hotspot both join. Pending. (Uriel)
- [ ] **PC IP correct everywhere.** From `ipconfig`: `EXPO_PUBLIC_API_URL=http://<IP>:8000` in `frontend/.env` (full reload after changing it), `APP_URL=http://<IP>:8081` and the `CORS_ORIGINS` entry in `backend/.env`. Pending. (Uriel, Jalen)
- [ ] **Windows Firewall** allows the backend (port 8000) and Metro (port 8081) on this network. VPN off. Pending. (Jalen)
- [ ] **Expo Go local network permission:** iPhone Settings > Privacy & Security > Local Network > Expo Go. **Check backend** shows "Backend: ok". Pending. (Uriel)
- [ ] **Anonymous phone-browser check** of the GC link, all six boxes in step 4. Pending. (Jalen, Uriel)
- [ ] **Email decision (pending Bona).** Either configure the test GC recipient (`GC_EMAIL`) and provider (`EMAIL_API_KEY`, `EMAIL_API_URL`, `EMAIL_FROM`) in the backend `.env` and get a test link delivered (check spam), or agree to the private console fallback. Keys stay in `.env`; never in the repository. Pending. (Bona, Jalen)
- [ ] **Test accounts** (B7): field, estimator and manager sign in on the live database. Passwords are shared privately. Seen working Nov 16 on a phone (all three, full workflow). Re-confirm Tuesday. (Bona)
- [ ] **Database password changed.** The database password was pasted in chat, a screenshot and a frontend variable during Nov 16 testing. Reset it in the Supabase dashboard (Project Settings, Database), update `backend/.env` for everyone who runs the backend, and share the new value privately. Pending. (Bona)
- [ ] **Sample photos** on the phone and the demo PC: three for step 1, two for step 6. No real job sites or people. Pending. (Uriel)
- [ ] **How the audience sees the phone** is decided and tested. Pending. (Bona)

#### Tuesday Nov 17: dry run (A1)

- [ ] Latest `main` pulled, `npm run install` re-run, backend tests, typecheck and lint pass.
- [ ] Backend, PC IP, `APP_URL`, CORS and Expo Go permission re-checked on the demo network. The IP can change overnight.
- [ ] **Demo data cleared or seeded.** The lists show only what the script expects. On Nov 16 the five test changes were deleted and the database holds only the seed (3 projects, 4 users, the company, no changes). After each dry run, clear what it created with a delete scoped to the demo company's changes (their photos, revisions, approvals, history and notifications), run by Bona. No drop, truncate or reset on the shared Supabase project. Uploaded photo files stay in the storage bucket until removed there.
- [ ] **Midday sign-in go/no-go (pending Bona).** All three accounts pass on the live database and in Expo Go: Path A. Otherwise Path B. Record the decision here: ____________
- [ ] **Account re-entry rehearsal** (step 5) done for all three accounts.
- [ ] Script run start to finish **twice**, timed. Target 14 minutes; the agenda allows 12, so note which step to shorten.
- [ ] Each fallback tried once: web preview for step 1, console link for step 4.
- [ ] Second run screen-recorded. Terminal 1 cropped or hidden in the recording so no link or token shows.
- [ ] List of everything that broke, with an owner each. Small PR per fix.
- [ ] **Claims check.** For each of these, write "seen working" or "not claimed": live database, sign-in, notifications, delivered email. The agenda below is edited to match.
- [ ] After the last fix is merged, no more changes to `main` before the meeting.

#### Wednesday Nov 18: 30 minutes before

- [ ] PC and phone on the demo network. `ipconfig` checked against `frontend/.env` and `backend/.env`.
- [ ] Two terminals: `npm run dev:backend`, then `npm run dev:frontend`; web build running for the GC page. App opened in Expo Go from the current QR code. "Backend: ok".
- [ ] Accounts ready (Path A) or role picker ready (Path B). Demo data as left on Tuesday.
- [ ] Phone charged, Do Not Disturb on, auto-lock off. Notifications off on the PC.
- [ ] Terminal 1 off the shared screen. Recording file opens.

---

## Part 2: Partner meeting agenda (DRAFT)

For Bona to paste into an email. Not sent to anyone. Recipients are left out on purpose, and the time and place are placeholders.

### Before sending (Bona)

- [ ] Fill in `[TIME]` and `[PLACE OR CALL LINK]`.
- [ ] After Tuesday's claims check, edit "What we built" and "What we will show". Keep a line only if it was seen working. Lines most at risk: the saved-in-a-database line (Supabase vs SQLite), sign-in, in-app alerts, and the emailed link. If real email is not delivered, change "emailed link" to "a link the GC opens".
- [ ] Attach or paste the one-page AI cost brief (B4, `docs/ai-cost-brief.md`) and the data summary (B5, `docs/data-status.md`). As of Nov 16 neither file is on `main`: they are on branches `b4-ai-cost-brief` and `b5-tad-data-status` and need review and merge first. Do not attach anything Tad's company sent.
- [ ] Status as of Nov 16 for the claims check: **seen working** are the live database (Jalen's restart check and Bona's phone run) and sign-in for all three accounts on a phone. **Not yet seen** are the emailed link (no provider is configured) and in-app alerts. Re-check all four on Tuesday.
- [ ] Check the sender line in ask 4 against what the email service really uses.
- [ ] If Tad has not yet answered who "Zach Smith" is in the Nov 4 notes and how the name is spelled, add it to ask 3.
- [ ] Remove the DRAFT markers.

### Email text

```text
Subject: DRAFT - ChangeOrder partner meeting, Wed Nov 18, [TIME] - agenda

DRAFT - not sent

Hi all,

Here is the agenda for our meeting on Wednesday, November 18 at [TIME], [PLACE OR CALL LINK]. It should take about 30 minutes. The main part is a live demo on a phone, and at the end we have six questions we need your answers on.

AGENDA

1. What we built since Nov 4 (4 min)
   - The specification is updated from our Nov 4 and Nov 5 meetings, with the roles renamed to field, estimator, manager and GC.
   - Change orders are now saved, so a server restart keeps them. [CONFIRM AFTER THE DRY RUN: which store, and whether the Supabase database is live]
   - The field user can attach several photos to one change.
   - The estimator adds a proposed cost and timeline in calendar days before anything goes to the general contractor (GC).
   - The GC opens a link and approves or declines without an account. Opening the link decides nothing; the GC confirms the decision.
   - High-priority changes have a fast track (see question 2).
   - [ONLY IF SEEN WORKING: Field, estimator and manager each sign in and see their own screens.]
   - [ONLY IF SEEN WORKING: The link reaches the GC by email.]

2. Live demo (12 min)
   What we will show, on a phone:
   - A field user photographs a change, describes it, sets a priority and submits it.
   - We restart the server and the change is still there.
   - The estimator adds the cost and timeline and sends it on.
   - The GC opens the link and approves or declines. Opening the link alone decides nothing.
   - The field user and the manager see the result.
   - The same again for a high-priority change, using the fast track.

3. AI budget and data status (5 min)
   - A one-page cost brief: expected usage per estimate, a monthly budget and a proposed model. [ATTACH OR PASTE SUMMARY]
   - Where we are on the data requested on Nov 5: what has arrived and what is still missing. [SUMMARY]

4. Questions for you (7 min)
   1. Role names. We now use field, estimator, manager and GC. Are these the right terms?
   2. Fast track. For a high-priority change, the manager authorizes the work to start right away. The estimate follows, and the GC still approves or declines the cost afterward. Nothing is approved by a timeout. Is this the rule you want?
   3. Data. Tad, where does the data from the Nov 5 request stand, and what date can we plan around for the first set?
   4. Email sender. The approval link reaches the GC by email. In real use, whose address should the GC see it come from?
   5. AI budget and model. Con, does the budget and the model in the cost brief look workable to you?
   6. Next meeting. What date and time suits everyone?

5. Next steps (2 min)
   - We read back the decisions and who owns each follow-up.

If you would like anything added, reply and I will include it.

Thanks,
Bona
```
