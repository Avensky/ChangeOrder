# Demo script and partner agenda: Wed Nov 18, 2026

Task B6. Owner: Bona. Written Nov 11, before most of the week's work is merged.

This file has two parts:

1. [The demo script](#part-1-demo-script), with a pre-demo checklist for Mon Nov 16 and Tue Nov 17.
2. [The partner meeting agenda](#part-2-partner-meeting-agenda-draft), as a draft email for Bona to send.

The script describes the **finished** behavior. Each step lists the task IDs it needs from [tasks/week-1.md](../tasks/week-1.md). Screen and button names are the planned ones and may differ in the build; correct the wording during the dry run (A1).

---

## Part 1: Demo script

**The one point to land:** a change reported from a phone is now saved in a real database, priced by the estimator, and decided by the GC from an emailed link, with no GC account.

**Length:** about 12 minutes for the six steps.

### What each step needs

| Step | What it shows | Needs these tasks | On `main` as of Nov 11 |
| --- | --- | --- | --- |
| 1 | Field submits with several photos and a priority | J1, U2 (several photos); B7, J5, U6 (sign-in); U1 (role names) | One photo only, no sign-in, old role names |
| 2 | Record survives a backend restart | B2, B3, J4 | No. Records are held in memory and are lost on restart |
| 3 | Estimator adds cost and timeline and sends it on | J2, U3 | No. The office step has no cost or timeline |
| 4 | GC decides from the emailed link | J3 (email), U4 (GC page), J2 (terms shown on the link) | The approval routes exist and the link is printed to the console. No email, no GC page |
| 5 | Field and manager see the result | B3, J4 (saved alerts); U3, U6 (manager screens) | Field sees the status. No manager screen |
| 6 | Fast track for a high-priority change | B2 (status), J2, U3, J3 (heads-up email) | No. Today the office approves a high-priority change with no GC decision |

If J2 is not merged by Tuesday, **skip step 6 and explain the rule in words**. Do not show today's behavior for a high-priority change: it skips the GC, which is the opposite of the rule we are asking Con to confirm.

### People and devices (proposed, Bona to confirm)

| Who | Does what |
| --- | --- |
| Bona | Narrates and runs the agenda |
| Uriel | Holds the phone: plays the field user |
| Jalen | Runs the demo PC: backend terminal, estimator, manager, and the GC's inbox |

| Device | Used for |
| --- | --- |
| Phone with Expo Go | Field user (steps 1, 2, 5, 6) |
| Demo PC, terminal 1 | Backend: `npm run dev:backend` |
| Demo PC, terminal 2 | Expo: `npm run dev:frontend` |
| Demo PC, browser window A | Web preview at `http://localhost:8081`, signed in as the estimator |
| Demo PC, browser window B (second browser or profile) | Web preview, signed in as the manager |
| Demo PC, private browser window | The GC link. A private window makes it plain that nobody is signed in |
| A team inbox that plays the GC | Receives the emailed link. Never use a real GC's address |

Estimator and manager run in the web preview so nobody has to sign out and in on the phone in front of the audience. If a second phone is free, the estimator can use it instead. Settle this at the dry run.

Run the backend and Expo in **two terminals**, not with `npm run dev`. `npm run dev` stops both when either one stops, and step 2 needs to stop only the backend.

### Step 1: Field reports a change

*Needs J1, U2, B7, J5, U6, U1. About 2 minutes.*

| | |
| --- | --- |
| **Who acts** | Field (Uriel, on the phone) |
| **Tap** | Open the app in Expo Go, already signed in as the field test account. Start a new change. Take or pick three photos. Enter the description. Leave priority at Normal. Submit. |
| **Say** | "A foreman sees something that is not in the contract. They take a few photos, say what it is and how urgent it is, and send it. The photos are for the people reviewing it; the AI does not read them." |
| **Audience sees** | Three photo thumbnails on the form, then the new change at the top of the field user's list with status `submitted`. |
| **Fallback** | **Phone cannot reach the backend:** open `http://<PC IP>:8000/health` in Safari on the phone. If that fails, check the PC IP in `frontend/.env` and the network (README, step 4 and Troubleshooting). If it still fails, do this step in the web preview at `http://localhost:8081` on the demo PC, signed in as field, with sample photos saved on the PC. **Camera fails or is slow:** pick the sample photos from the phone's library. **Several photos not merged (J1, U2):** attach one photo and say several are coming. |

Sample text: "Owner asked to move the hose bib from the north wall to the east wall. Not in the original proposal."

### Step 2: Restart the backend

*Needs B2, B3, J4. About 1.5 minutes. This is the point of the week.*

| | |
| --- | --- |
| **Who acts** | Jalen on the demo PC, then the field user on the phone |
| **Tap** | In terminal 1 press Ctrl+C. Wait for the backend to stop. Run `npm run dev:backend` again and wait for "Application startup complete". On the phone, reload the list of changes. |
| **Say** | "On Nov 4 this lived in the server's memory. Restart the server and everything was gone. It is now saved in a database, so watch what happens when we turn the server off and on." |
| **Audience sees** | The backend stopping and starting in the terminal. Then the same change, with its three photos and status `submitted`, still in the list on the phone. |
| **Fallback** | **Backend does not come back:** read the error in terminal 1, start it once more. **Phone shows an empty list or an error:** open the list in the web preview. **Still missing in the app:** show the row in the Supabase table view on the PC (Bona's sign-in, table view only, no settings or keys on screen). **The record is really gone:** say so plainly and move on. Do not work around it; this is the result the week was for. |

Do not save any file under `backend/` during the demo. The backend runs with auto-reload and restarts on every save.

### Step 3: Estimator prices it

*Needs J2, U3 (and B7, J5, U6 for sign-in). About 2 minutes.*

| | |
| --- | --- |
| **Who acts** | Estimator (Jalen, browser window A) |
| **Tap** | Open the submitted change. Look at the photos. Enter the description for the GC, the requested timeline, and the proposed cost. Send to GC. |
| **Say** | "The estimator checks whether this is in scope, writes up the change, and sets the price and the time. The estimator decides the number. Later the AI will suggest one, but it never approves anything." |
| **Audience sees** | The estimator's screen with the field photos and description, the cost and timeline fields filled in, then status `awaiting_gc`. On the phone, the field user's copy shows `awaiting_gc` after a reload. |
| **Fallback** | **Estimator screen fails in the web preview:** sign in as estimator on the phone and do it there. **Screen not merged (U3) but the route is (J2):** call the estimator route from the API page at `http://localhost:8000/docs`. With role checks on (J5) that page needs the estimator's sign-in token, so rehearse this on Tuesday or drop it. **Neither merged:** stop the live demo here and talk through steps 3 to 6 from the workflow diagram in the spec. |

Sample values: timeline 2 working days, cost $850.00.

### Step 4: GC decides from the email

*Needs J3, U4, J2. About 2 minutes.*

| | |
| --- | --- |
| **Who acts** | GC (Jalen, private browser window on the demo PC) |
| **Tap** | Open the GC inbox. Open the email. Click the link so it opens in the private window. **Stop. Do not press anything.** Reload the field user's list on the phone to show the status has not changed. Then, on the GC page, press Approve. |
| **Say** | "The general contractor does not have our app and will never sign in. They get an email. Opening the link shows them the exact proposal: description, cost, timeline. Opening it decides nothing, so a mail scanner or a stray click cannot approve a change. Only pressing the button does." |
| **Audience sees** | The email with the link. The GC page with the description, photos, cost and timeline, and two buttons: Approve and Decline. No sign-in screen. Status still `awaiting_gc` after the link is opened. Status `approved` only after the button press. |
| **Fallback** | **Email is not set up or does not arrive within about 20 seconds:** copy the link from terminal 1. The backend prints it every time, and it works without an email key. Say that this is the same link the email carries. **Link does not open:** check which address it points to. On Nov 11 the printed link points to `localhost:8081`, which opens only on the demo PC, not on a phone. **GC page not merged (U4):** show the proposal from the approval route on the API page at `http://localhost:8000/docs` and record the decision from there. |

To show a decline as well, seed one change that is already at `awaiting_gc` and keep its link in a private note (never in the repository). Open it, press Decline, and show status `declined`. Do this only if there is time.

### Step 5: Field and manager see the result

*Needs B3, J4 (alerts saved); U3, U6 (manager screens). About 1 minute.*

| | |
| --- | --- |
| **Who acts** | Field (phone) and manager (browser window B) |
| **Tap** | On the phone, reload the list and open the change. In window B, open the manager's list and the same change. |
| **Say** | "Everyone who needs to know is told. The foreman can see on site that the work is approved. The manager sees it in the office." |
| **Audience sees** | Status `approved` on the phone and on the manager's screen, and an in-app alert for each if alerts are built. |
| **Fallback** | **Status does not update:** fully reload the app (close and reopen Expo Go) or the browser tab. **Alerts are not shown:** show the status on the change itself and say alerts are next. **Manager screen not merged:** show the estimator's list in window A instead and say the manager sees the same. |

### Step 6: Fast track for a high-priority change

*Needs B2, J2, U3, J3. About 3.5 minutes.*

| | |
| --- | --- |
| **Who acts** | Field (phone), then manager (window B), then estimator (window A), then GC (private window) |
| **Tap** | **Field:** new change, two photos, description, priority High, submit. **Manager:** open it and press Authorize work now. **Field:** reload and show the new status. **Estimator:** open it, add cost and timeline, send to GC. **GC:** open the new email link, read the cost, press Approve (or Decline). **Field and manager:** reload. |
| **Say** | "Some changes cannot wait for an estimate. For a high-priority change the manager authorizes the work to start now. The estimate follows, and the GC still approves or declines the cost. Nothing is ever approved by a timeout. Con, this is the rule we would like you to confirm today." |
| **Audience sees** | Status `submitted`, then `authorized_to_proceed` right after the manager's press, with no cost yet. A heads-up email to the GC saying work has started. After the estimator sends it: `awaiting_gc` and a second email with the link and the cost. After the GC's press: `approved` (or `declined`) on the phone and the manager's screen. |
| **Fallback** | **Heads-up email missing:** say it is sent in the finished version and carry on; the link for the decision is still in terminal 1. **Authorize action fails in the app:** call the manager route from the API page (same token caveat as step 3). **J2 not merged:** skip this step and explain the rule from the spec diagram. Do not demonstrate the old high-priority behavior. |

Sample text: "Supply line is leaking behind the wall in unit 204. Drywall closes tomorrow morning, so the repair has to start today." Sample values: timeline 1 working day, cost $2,400.00.

### If the live demo cannot run at all

Play the screen recording made at Tuesday's second dry run and narrate over it. Say that it is a recording.

### Pre-demo checklist

Tick each line. The person named does the check; everyone confirms at the dry run.

#### Monday Nov 16: setup

- [ ] **Backend running.** `npm run dev:backend` starts on the demo PC with no errors and `http://localhost:8000/health` returns `{"status":"ok"}`. (Jalen)
- [ ] **Database reachable.** The backend's `.env` on the demo PC points at the Supabase project, and a test change is still there after a restart. Needs B3; J4 may land Tuesday. (Bona)
- [ ] **Demo network chosen and tested.** Decide which network the meeting will use. Put the PC and the phone on it and open `http://<PC IP>:8000/health` in Safari on the phone. Some campus and guest networks stop devices from talking to each other; if this one does, use a phone hotspot that both the PC and the demo phone join, and test that instead. (Uriel)
- [ ] **PC IP in `frontend/.env` correct.** Run `ipconfig`, take the IPv4 address of the adapter on the demo network (not a VPN or virtual adapter), and set `EXPO_PUBLIC_API_URL=http://<that address>:8000`. Fully reload the app afterward; Fast Refresh keeps the old value. See README step 4. (Uriel)
- [ ] **Windows Firewall** allows the backend's Python on this network (README, Troubleshooting). VPN off on the PC. (Jalen)
- [ ] **Expo Go local network permission** is on: iPhone Settings > Privacy & Security > Local Network > Expo Go. The app's Home screen shows the right address and **Check backend** shows "Backend: ok". (Uriel)
- [ ] **Test accounts.** The field, estimator and manager test accounts from B7 each sign in and see only their own screens. Passwords are shared privately, never written here. (Bona)
- [ ] **Email.** Either the email key is set in the backend's `.env` and a test link reaches the GC inbox, or the team agrees to use the console link on Wednesday. Check the spam folder. (Jalen, Bona)
- [ ] **GC link address.** The link in the email and in the console opens on the device that will play the GC. (Jalen)
- [ ] **Sample photos** saved on the phone and on the demo PC: three for step 1, two for step 6. No real job sites, people or addresses from Tad's company. (Uriel)
- [ ] **How the audience sees the phone** is decided and tested: mirrored to a screen, held under a camera, or passed around. (Bona)
- [ ] **Unmerged tasks listed.** Go through the "What each step needs" table and write down which steps will run live and which will be explained. (Bona)

#### Tuesday Nov 17: dry run (A1)

- [ ] Latest `main` pulled on the demo PC, `npm run install` re-run, backend tests pass.
- [ ] **Backend running** and **PC IP in `frontend/.env`** re-checked on the demo network. The IP can change overnight.
- [ ] **Expo Go local network permission** still on; "Backend: ok" on the phone.
- [ ] **Demo data cleared or seeded.** The lists for the demo company show only what the script expects: empty, or the seeded changes below. Clearing is Bona's job and touches only the demo company's test records. No drop, truncate or reset on the shared Supabase project.
  - [ ] Optional seed: one change already `approved`, so the lists are not empty.
  - [ ] Optional seed: one change at `awaiting_gc` with its link saved privately, for the decline in step 4.
- [ ] **Test accounts signed in** where the device table says: field on the phone, estimator in window A, manager in window B. GC inbox open in its own tab.
- [ ] Script run start to finish **twice**, timed. Target 12 minutes.
- [ ] Each fallback tried once: web preview for step 1, console link for step 4.
- [ ] Second run screen-recorded, phone and PC, and the file kept on the demo PC.
- [ ] Everything that broke is listed, with an owner for each fix. Small PR per fix.
- [ ] Wording in this script corrected to match the real screen and button names.
- [ ] After the last fix is merged: no more changes to `main` before the meeting.

#### Wednesday Nov 18: 30 minutes before

- [ ] PC and phone on the demo network. `ipconfig` checked against `frontend/.env`.
- [ ] Two terminals started: `npm run dev:backend`, then `npm run dev:frontend`. App opened in Expo Go from the current QR code. "Backend: ok".
- [ ] Accounts signed in as on Tuesday. Demo data as left on Tuesday.
- [ ] Phone charged, Do Not Disturb on, auto-lock off. Notifications off on the demo PC.
- [ ] Terminal 1 visible and readable for step 2 and for the console link.
- [ ] Recording file opens.

---

## Part 2: Partner meeting agenda (DRAFT)

For Bona to paste into an email. Not sent to anyone. Recipients are left out on purpose, and the time and place are placeholders.

### Before sending (Bona)

- [ ] Fill in `[TIME]` and `[PLACE OR CALL LINK]`.
- [ ] Under "What we will show", remove anything that is not merged and working after Tuesday's dry run. Each line depends on: saved in a database (B2, B3, J4); several photos (J1, U2); estimator cost and timeline (J2, U3); emailed GC link (J3, U4); fast track (J2, U3); staff sign-in (B7, J5, U6).
- [ ] Attach or paste the one-page AI cost brief (B4, `docs/ai-cost-brief.md`) and take the data summary from B5 (`docs/data-status.md`). Neither exists as of Nov 11.
- [ ] Check the sender line in ask 4 against what the email service really uses.
- [ ] If Tad has not yet answered who "Zach Smith" is in the Nov 4 notes and how the name is spelled (B5), add it to ask 3.
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
   - Change orders are now saved in a database. Before, they were lost whenever the server restarted.
   - The field user can attach several photos to one change.
   - The estimator adds a proposed cost and timeline before anything goes to the general contractor (GC).
   - The GC gets an emailed link and approves or declines without an account.
   - High-priority changes have a fast track (see question 2).
   - Field, estimator and manager each sign in and see their own screens.

2. Live demo (12 min)
   What we will show, on a phone:
   - A field user photographs a change, describes it, sets a priority and submits it.
   - We restart the server and the change is still there.
   - The estimator adds the cost and timeline and sends it on.
   - The GC opens the emailed link and approves or declines. Opening the link alone decides nothing.
   - The field user and the manager see the result.
   - The same again for a high-priority change, using the fast track.

3. AI budget and data status (5 min)
   - A one-page cost brief: expected usage per estimate, a monthly budget and a proposed model. [ATTACH OR PASTE SUMMARY]
   - Where we are on the data requested on Nov 5: what has arrived and what is still missing. [SUMMARY]

4. Questions for you (7 min)
   1. Role names. We now use field, estimator, manager and GC. Are these the right terms?
   2. Fast track. For a high-priority change, the manager authorizes the work to start right away. The estimate follows, and the GC still approves or declines the cost afterward. Nothing is approved by a timeout. Is this the rule you want?
   3. Data. Tad, where does the data from the Nov 5 request stand, and what date can we plan around for the first set?
   4. Email sender. The approval link reaches the GC by email. For the demo it comes from [SENDER USED IN THE DEMO]. In real use, whose address should the GC see it come from?
   5. AI budget and model. Con, does the budget and the model in the cost brief look workable to you?
   6. Next meeting. What date and time suits everyone?

5. Next steps (2 min)
   - We read back the decisions and who owns each follow-up.

If you would like anything added, reply and I will include it.

Thanks,
Bona
```
