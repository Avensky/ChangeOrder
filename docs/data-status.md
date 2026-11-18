# Training data from Tad: status

Task B5. Tracks the data requested from Tad (Zack Smith Plumbing) on Nov 5, 2026 to train the AI cost estimator. Source for the request: the "AI cost estimation" section of [SPECIFICATIONS-v0.2.MD](../SPECIFICATIONS-v0.2.MD).

**Never commit Tad's company data to this repository.** Not the files, not excerpts, not screenshots, not real amounts or names copied into this page. The data is covered by a signed NDA and stays outside the repository. This page records only what was asked for and whether it has arrived.

## Where things stand

- Nov 5: Bona met Tad. An NDA is signed.
- After the meeting: Bona emailed Tad a detailed outline of the request.
- Tad's estimator was out when they met, so timing is unknown.
- Wed Nov 18 (morning): Bona received five original project proposals and the five change orders for those projects from Tad. That is the minimum tier (rows 1 and 2). The files are kept outside this repository.
- Tad is also preparing the matching invoices for the five change orders, expected from his accounting department within a couple of days of Nov 18. Bona asked for the final billed amount, the invoice date with a paid or approved marker, a labor and materials breakdown if available, a project and change order label on each invoice, and the same redaction as the first set. Row 1 stays `received` and gains the invoices when they arrive.
- The Nov 13 follow-up is no longer needed for rows 1 and 2. The draft below is kept for reference only; edit it before any further request for the full tier (rows 3 to 8).

**Bona updates the status column.** Rows 1 and 2 are `received` on Bona's word (Nov 18). Rows 3 to 8 stay "Bona to confirm": this page was written without access to Bona's email or to anything Tad has sent, so nothing here says whether those items have or have not arrived.

## Checklist of the Nov 5 request

Status values for Bona to use: `received`, `partial` (say what is missing), `not received`, `not expected` (Tad will not share it).

| # | Item | Why we need it | Tier | Concern Tad raised | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Completed change order examples, each with the original request, final proposal, revisions, approval, final amounts and dates | The core examples the AI learns from: what was reported, how it was priced, and what was finally approved | Minimum (a handful); full (many more) | None recorded in the spec | `received` (Nov 18: five proposals and the five change orders for them) |
| 2 | Original project proposals | The scope baseline. Tad's rule: anything absent from the original proposal is flagged as a likely change order | Minimum (the proposals behind the change orders in row 1); full (many more) | None recorded in the spec | `received` (Nov 18: five proposals and the five change orders for them) |
| 3 | Labor hours and rates by trade | Cost breakdown, so a suggested cost can be built from hours and rates instead of a single total | Full | See row 8: rates may only be shareable as a redacted breakout | Bona to confirm |
| 4 | Materials and quantities | Cost breakdown for the materials part of an estimate | Full | None recorded in the spec | Bona to confirm |
| 5 | Equipment, subcontractor quotes, permits, overhead, markup, tax | The rest of the cost breakdown, so a suggestion covers the whole price and not only labor and materials | Full | None recorded in the spec | Bona to confirm |
| 6 | Foreman daily reports, only those tied to change orders | Field context for a change: what the crew saw and did on the day | Full | There are plenty, but they are not yet redacted, so Tad will share only the ones tied to change orders | Bona to confirm |
| 7 | Supplier quotes | Real material prices behind an estimate | Full | None. Tad said these are easy to provide | Bona to confirm |
| 8 | Redacted bid-sheet breakout of labor rates and expenses | Stands in for the full bid sheets, giving the rates and expenses behind a price | Full | Bid sheets may be proprietary, so Tad will try a redacted breakout instead of the sheets themselves | Bona to confirm |

Notes on the table:

- The tier for rows 6, 7 and 8 is read from the spec, which names only proposals with their change orders as the minimum. Bona, correct it if the outline you sent says otherwise.
- "None recorded in the spec" means the spec lists no concern for that item. It does not mean Tad has none.

## What we do with it

- **Minimum tier (proof of concept):** a handful of original proposals with their change orders (rows 1 and 2). That is enough to show the AI checking a reported change against the original scope and suggesting a cost, with the estimator making the final call.
- **Full tier (accurate estimates):** much more. Many more proposals and change orders, plus the cost breakdowns and supporting documents in rows 3 to 8. This is what makes the suggested costs accurate enough to be useful.

The AI stays advisory in both tiers. It suggests scope and cost, and the estimator decides.

## Follow-up email to Tad

> **DRAFT. Not sent. Superseded for rows 1 and 2: they arrived Nov 18.** Only Bona sends anything to Tad, and only for items still missing. No agent sends it. Bona, edit it to match the outline you actually sent before sending.

**To:** Tad
**Subject:** Checking in on the change order examples

Hi Tad,

Thanks again for meeting with us on Nov 5. I wanted to check in on the outline I sent afterward. I know your estimator was out that week, so there is no pressure on timing.

The smallest thing that would get us started is a handful of original project proposals, each with its change orders: the original request, the final proposal, any revisions, the approval, and the final amounts and dates. That is enough for a proof of concept. Everything else on the outline can follow later.

If redacting is what takes the time, we are glad to change the approach. We could start with fewer documents, take the labor and expense breakout in place of the bid sheets, or leave the daily reports out for now. Tell us what is easiest for you and we will work with it.

One more question. Our notes from Nov 4 say approval goes "back to Zach Smith". Who is that in your process: a person, such as your boss, the company itself, or someone else?

Thanks,
Bona

Optional for Bona: the spec also has an open question on the spelling of the partner's name (Zack or Zach Smith). It is left out of the draft to keep it to one question, and Tad's reply may answer it anyway.
