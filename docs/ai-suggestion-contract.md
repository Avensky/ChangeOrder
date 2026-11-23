# AI suggestion contract (task B9)

For Jalen (task J7) and Uriel (task U7). Bona owns the worker and the tables. This page is the agreed shape, so routes and screens can be built before the AI runs.

The suggestion is **advice for the estimator**. It decides nothing, never approves anything, never fills in the estimator's cost on its own, and takes no photos.

## What the worker does

`backend/ai/suggest.py`, `suggest(...)`:

```python
suggest(*, change_description: str, original_proposal: str,
        examples: Sequence[Example] = (), model_id=None, region=None, client=None) -> SuggestionResult
```

- `original_proposal` is the **original** proposal text for the change's project, not a revised one. The route (J7) loads it. Where it comes from this week is Bona's decision (B8); until then pass the text in.
- `examples` are optional past change orders with their billed lump sums, for calibration: `Example(description, billed_cents)`.
- It calls Bedrock with a **US inference profile only** (`us.anthropic.claude-sonnet-5-5` or `us.anthropic.claude-haiku-5-5`) in a US region. Anything else raises `SuggestionUnavailable` before any call.
- Errors: `SuggestionUnavailable` (cannot reach or not allowed: return 503 with "AI suggestions are not available. The office can enter cost and days manually.") and `SuggestionError` (the reply was unusable: return 502). Neither message ever contains document text.
- Settings (backend `.env`): `BEDROCK_MODEL_ID` and `AWS_REGION`. Never put keys in the repo.

`SuggestionResult` has: `in_scope` (bool), `scope`, `cost_low_cents`, `cost_cents` (the best estimate), `cost_high_cents`, `timeline_days`, `rationale`, `confidence` (0 to 1), `model_id`, `prompt_version`, and token counts. `result.as_repository_dict()` gives the dict the repository takes.

The cost is a **lump-sum range in USD cents**. There is no labor and materials breakdown, because the partner prices and bills change orders as lump sums.

## What the repository gives you

All in `backend/db/repository.py`, inside `atomic()`, filtered by company:

| Function | Use |
| --- | --- |
| `create_suggestion(change_id, suggestion, original_scope)` | Store one suggestion for a `submitted` or `in_review` change and return the stored row (with `id`). `save_suggestion` does the same and returns what it was given, for the old callers. |
| `list_suggestions(change_id)` | A change's suggestions, newest first. NotFound for another company's change. |
| `respond_to_suggestion(suggestion_id, response, actor_user_id, rating=None)` | Record `accepted`, `edited` or `dismissed`, with an optional rating from 1 to 5. A suggestion is answered once; a second answer is a Conflict (409). Bad values raise ValueError (422). |

A stored suggestion is a dict:

```json
{
  "id": 7, "change_id": "12",
  "in_scope": false,
  "scope": "Add three roof drains with storm piping.",
  "original_scope": "...", "rationale": "...",
  "currency": "USD",
  "cost_cents": 620050, "cost_low_cents": 500000, "cost_high_cents": 750000,
  "amount": 6200.5,
  "impact_days": 2,
  "confidence": 0.7,
  "model_id": "us.anthropic.claude-sonnet-5-5", "prompt_version": "2026-11-23.1",
  "created_at": "2026-11-24T18:00:00+00:00",
  "response": null, "rating": null, "responded_by_id": null, "responded_at": null
}
```

`amount` is the legacy dollars key. New code should use the `_cents` fields. `cost_low_cents` and `cost_high_cents` are null on suggestions stored before this change.

## Suggested routes (Jalen decides the names)

- `POST /changes/{id}/suggestion`: estimator only. Loads the proposal, calls the worker, stores and returns the suggestion.
- `GET /changes/{id}/suggestions`: any staff role that can see the change.
- `POST /suggestions/{id}/response`: estimator only. Body `{response, rating?}`. The caller's user id comes from the verified token, never from the body.

Answering a suggestion records the estimator's choice and nothing else. The estimator still enters the cost on the review screen.

## What the screen shows (Uriel)

Label it clearly as a suggestion. Show the scope flag, the cost range and best estimate, the timeline, the rationale and the confidence. Let the estimator accept, edit or dismiss it and give a rating. Show "AI suggestions are not available" without blocking the review when the route returns 503.

## Database

`backend/db/migrations/0003_ai_suggestion_v2.sql` adds the range, prompt version, response, rating, who and when. It is **not yet run on the shared Supabase project**; Bona runs it. The SQLite tests use the models, so they work now.
