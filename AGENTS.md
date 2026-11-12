# Agent rules for ChangeOrder

These rules apply to every coding agent on this repository (Claude Code, ChatGPT, or any other), and to the people running them. Read this file first, then your task in [tasks/week-1.md](tasks/week-1.md).

ChangeOrder helps field workers report a change to contracted work, lets the office price it, and gets the general contractor's approval from an emailed link. The full design is in [SPECIFICATIONS-v0.2.MD](SPECIFICATIONS-v0.2.MD). `frontend/AGENTS.md` adds Expo-specific rules for anything under `frontend/`.

## Roles (confirmed Nov 11, 2026)

| Person | Role | Area they own |
| --- | --- | --- |
| Bona | Project coordinator, database lead, AI lead | `backend/db/`, `backend/ai/`, migrations, `docs/` outside the spec |
| Jalen | Backend API lead | `backend/api/`, `backend/schemas/`, `backend/services/`, `backend/tests/` |
| Uriel | Frontend lead, architecture and specification owner | `frontend/`, `SPECIFICATIONS-v0.2.MD` |

An agent works for the person who started it and edits only that person's area. If a task needs a change in someone else's area, do not make it: describe what is needed in the PR description and ask that person.

Two rules protect shared files:

- Only Bona's agents change `backend/db/models.py` and the migrations. There is one writer for the database.
- Anyone who adds a dependency (`backend/requirements.txt`, `frontend/package.json`) says so in the PR description.

## Working on a task

1. Read your task in `tasks/week-1.md`: owner, due date, dependencies, "done when", files you may edit.
2. Create a branch from the latest `main` named `<task-id>-<short-slug>`, for example `b2-schema-v2`. One task per branch.
3. Do only that task. Stay inside the files the brief allows.
4. If the task depends on work that is not merged yet, code against the agreed contract (the repository function signatures or `docs/openapi.json`) with a fake or stub. Do not wait, and do not edit the other person's area to unblock yourself.
5. Run the checks below, then open a pull request to `main` using the PR template.

## Commands

Run from the repository root unless noted.

| Purpose | Command |
| --- | --- |
| Install everything | `npm run install` |
| Run backend and app | `npm run dev` |
| Backend tests (Windows) | `cd backend` then `.\.venv\Scripts\python.exe -m unittest discover -s tests` |
| Backend tests (Linux, CI) | `cd backend && python -m unittest discover -s tests` |
| Frontend types | `npm run typecheck` |
| Frontend lint | `npm run lint` |
| Refresh the API description | `cd backend && python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))" > ../docs/openapi.json` |

## Definition of done

- The "done when" line in the task brief is true, and the PR description says how you checked it.
- Backend tests pass, `npm run typecheck` and `npm run lint` pass. The GitHub check runs the same commands and a PR cannot merge while it fails.
- If routes or schemas changed, `docs/openapi.json` is refreshed in the same PR.
- Anything you could not check automatically, such as behavior on a phone, is listed in the PR description as a manual test with its result.
- No secrets, `.env` files, or personal data in the diff.

## Pull requests and review

- Open small PRs, at least daily. Rebase on `main` before opening.
- A person reviews and merges every PR. Agents never merge and never push to `main`.
- Reviewers: Jalen reviews Bona's database-facing changes and Uriel's API-facing changes. Bona reviews Jalen's schema use. Uriel reviews Jalen's API contract changes.
- An agent may do a first-pass review in a separate session, but that does not replace the human review.

## Guardrails

- Never commit or print `.env` values, Supabase keys, email keys, or tokens. Keys live in each person's local `.env` and in the host's secret settings.
- Never delete or rewrite another person's branch.
- Never run destructive database commands (drop, truncate, reset) against the shared Supabase project. Use migrations, reviewed in a PR.
- Do not edit `SPECIFICATIONS.MD` (v0.1). The current spec is `SPECIFICATIONS-v0.2.MD`; change it only through Uriel.

## Domain rules every agent must follow

- **Personas:** field, estimator, manager, GC. Do not introduce "client" or "contractor" in new code or UI text. Old names in existing code are renamed by tasks B2 and U1.
- **GC approval is external.** The GC never signs in. They act through an emailed link with a random token; only its hash is stored. Opening the link must never approve or decline; only an explicit button press does.
- **Fast track:** for a high-priority change the manager authorizes work to start before the estimate. The estimator then adds the cost, and the GC still approves or declines it. A timeout never approves anything.
- **Statuses** (one set for code and database): `submitted`, `in_review`, `authorized_to_proceed` (fast track only), `awaiting_gc`, `approved`, `declined`, `withdrawn`.
- **Photos** are context for people, not AI input. Several photos per change. Photos should not be served from a public folder in the long term.
- **AI is advisory.** It suggests scope and cost; the estimator decides. It never approves anything.
- **Money** is stored as integer cents with a currency, never floats.
- **Tenants:** every record belongs to a company, and every query filters by it.
- **Staff sign-in** uses Supabase accounts. The server derives the caller's role from the verified token and never trusts a role or company sent by the app.

## When something is unclear

Do not guess on rules that affect who can authorize work or what a GC sees. Put the question in the PR description and flag it for Bona. Open decisions are listed at the end of `SPECIFICATIONS-v0.2.MD`.
