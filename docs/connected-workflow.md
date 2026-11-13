# Connected roles, photos, and work orders

This branch combines the role workspace UI from #9 and multi-photo API from #10 with their integration. Merge this PR instead of merging those two independently. It does not include #7 or #8.

## Run and try it

Use the existing README setup. Set `EXPO_PUBLIC_API_URL` to the backend address reachable by your phone. When configured, the app opens in connected mode; Settings can switch between the connected workspace and a separate local demo. The server refreshes connected records every five seconds.

1. Preview Subcontractor or Contractor. Report a change with a title, project, description, priority, and up to ten photos (10 MB each).
2. Switch to Office Manager. Open the report, inspect all attachments, and enter the proposed scope, dollar amount, and whole number of additional days.
3. Send normal-priority terms for approval. Switch to Approver and approve or decline. The approval link in the server's client notification also opens `/approve?token=…` directly.
4. Open Projects, then the project's work order. Approval automatically adds the reviewed scope, amount, schedule impact, and photo references. Pending and declined changes do not contribute. Retrying a decision returns 409 and cannot add the same change twice.
5. Reload the app or restart the API. Connected records, history, approval tokens, and notifications remain saved.

The existing urgent prototype policy is retained: high-priority office review approves the change immediately and therefore updates the work order. The separate workflow described by specification v0.2 (authorize urgent work, then estimate and GC approval) is not implemented here.

The role picker still previews roles; it is not user authentication or server-enforced access control. Subcontractor UI filters are by submitter role, not by signed-in individual. Use this prototype with trusted demo participants. Production identities and project membership require the planned authentication work.

## Local persistence

`services/store.py` uses a transactionally saved SQLite workspace snapshot, defaulting to `backend/workspace.sqlite3`; override with `WORKSPACE_DB_PATH`. Every transaction takes SQLite's write lock and reloads state so multiple API workers cannot lose decisions. Approval state, history, and notification changes commit together. This local prototype store is independent of the unimplemented Supabase schema/migrations in `db/models.py`. Back up the database and `backend/uploads/` together. Existing in-memory sessions have no saved data to migrate.

Work order additions are derived from committed approved changes rather than appended by a background job. Each change contributes once. Days are summed sequentially; this is not critical-path scheduling. Project base budgets and names remain sample configuration in the frontend; the API returns approved additions, not a real baseline contract total.

`APP_URL` sets the base address in approval links (for example your phone-accessible frontend URL). The default is `http://localhost:8081`. These prototype links have no expiry or revocation yet. In-app role preview decisions use the same token-backed routes as the link screen. Notifications are stored in the app; no SMS/email/push delivery is configured.

## Optional AI suggestions

Install the backend requirements and configure `BEDROCK_MODEL_ID`, `AWS_REGION`, and the server's normal AWS credential chain with permission to invoke that model through Bedrock Converse. Choose a model supporting image input. No AWS credentials belong in the mobile frontend.

Office Manager can paste the original approved scope and request a suggestion. The request includes the reported description and supported JPEG/PNG/WebP attachments up to 3.75 MB each. Other uploaded formats remain viewable by people but are excluded from AI input, with the attachment count sent to the model. Model availability, image dimensions, and permissions depend on the chosen Bedrock model.

The model returns suggested scope, cost, additional days, likely scope classification, and assumptions. The office must choose **Use suggestion for review**, edit the terms as needed, and explicitly send them. Suggestions never approve a change or update a work order. The original report is retained separately from the reviewed proposal scope.

Without model configuration the endpoint returns a clear 503 and manual estimating remains usable. Invalid model output returns 502; service/credential errors return 503. Live model accuracy and AWS access must be validated in the target deployment. Automated tests use a mocked model and verify suggestions cannot mutate approval state.

## Contract changes

- `POST /api/v1/changes`: repeated `photos` files; optional `title`, `project_id`, `submitted_by`; response includes `photo_keys`, metadata, terms, and history.
- `POST /api/v1/changes/{id}/admin-approve`: required JSON `{amount, impact_days, scope?}`. Dollars must be nonnegative with at most two decimal places, days a nonnegative integer. Sent terms cannot be overwritten.
- `POST /api/v1/changes/{id}/suggestion`: JSON `{original_scope}`; advisory response only.
- `GET /api/v1/projects/{project_id}/work-order`: committed approved additions and revision count.

`docs/openapi.json` is generated from this branch's running schemas.
