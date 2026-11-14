# AI cost brief (task B4)

For Con, to judge feasibility. Prepared for Bona. All prices were read on **Nov 11, 2026** from the AWS pages listed under [Sources](#sources), are in US dollars before tax, and are pay-as-you-go ("on-demand") rates for US regions.

**Bottom line.** With the recommended model, the AI costs about **4 cents per change order**. Starting with 1 GB of data, expect about **$7 to $50 a month** for 50 to 1,000 change orders. Each extra GB of data adds about $5 a month. The worst case modeled here is **under $400 a month**. AWS credits pay up to $100 until they expire around Apr 13, 2027, about 5 months away, and Cohyric pays after that; see [Who pays](#who-pays).

**Decided by Bona on Nov 13, 2026.** Tad's data stays on US servers at all times. We start with a small amount of data and add more as needed. AWS credits pay up to $100, then Cohyric pays. The figure of 1.5 AI runs per change order stands until it can be tested on Tad's data.

**The Nov 4 figures are not confirmed.** The notes quoted about $0.02 per 1M input tokens and about $10 per 10M output tokens ($1 per 1M). No text model in the US-region tables of the Bedrock pricing page has those prices; the cheapest input price I found is $0.035 per 1M [1]. $0.02 per 1M is the price of Amazon Titan Text Embeddings V2, a search-indexing model that cannot write an answer [1]. The recommended model costs $2.20 per 1M input and $11.00 per 1M output, which is 110 times and 11 times the Nov 4 figures. The budget is still small because each estimate uses few tokens.

## 1. What the AI does per change order

When a change order is reported, the AI reads it next to the job's original proposal and a few similar past change orders pulled from the knowledge base. It suggests whether the work is already in scope of the original proposal, and what it might cost, with a reason and a confidence. It is advisory: the estimator decides, and the AI never approves anything. Photos are not sent to the AI.

## 2. Token usage per estimate

A token is a piece of a word. Models are billed per token read (input) and per token written (output).

Nothing below is measured yet, because Tad's documents have not arrived. Page counts are converted at **700 tokens per page**, a rule of thumb (about 500 words a page, about 0.75 words per token).

| Part of one AI run | Low | Expected | High |
| --- | ---: | ---: | ---: |
| Instructions to the model | 400 | 700 | 1,200 |
| Original proposal (2, 6 or 25 pages × 700) | 1,400 | 4,200 | 17,500 |
| The change order as reported | 150 | 400 | 1,000 |
| Knowledge-base passages (5 × 300, 10 × 400, 20 × 500) | 1,500 | 4,000 | 10,000 |
| **Input per run** (sum of the four rows) | **3,450** | **9,300** | **29,700** |
| **Output per run** (the answer) | **300** | **800** | **3,000** |
| Runs per change order (re-asks after edits) | 1 | 1.5 | 3 |
| **Input per change order** (input × runs) | **3,450** | **13,950** | **89,100** |
| **Output per change order** (output × runs) | **300** | **1,200** | **9,000** |

Notes on the assumptions:

- A knowledge-base passage is about 300 tokens by default [6].
- Both Claude models reason before they answer by default [4][5]. I assume that reasoning is billed as output; the high case allows for it. Not verified on an AWS page.

## 3. Monthly budget

Uses the recommended model, Claude Sonnet 5.5, at $2.20 per 1M input tokens and $11.00 per 1M output tokens [1], and the managed knowledge base from section 5.

**Cost of one change order** = input tokens × $2.20 ÷ 1,000,000 + output tokens × $11.00 ÷ 1,000,000

| Case | Input cost | Output cost | Per change order |
| --- | --- | --- | ---: |
| Low | 3,450 × 2.20 ÷ 1M = $0.00759 | 300 × 11 ÷ 1M = $0.00330 | **$0.01089** |
| Expected | 13,950 × 2.20 ÷ 1M = $0.03069 | 1,200 × 11 ÷ 1M = $0.01320 | **$0.04389** |
| High | 89,100 × 2.20 ÷ 1M = $0.19602 | 9,000 × 11 ÷ 1M = $0.09900 | **$0.29502** |

**Monthly total** = model + retrieval + storage, each rounded to the cent.

- Model = change orders × cost per change order.
- Retrieval = change orders × runs × $0.001 (one knowledge-base lookup per run, at $1.00 per 1,000 lookups [1]).
- Storage = data size × ($5.00 knowledge-base index [1] + $0.023 S3 file storage [2]) per GB per month. We start with 1 GB, which is $5.02 a month. The worst case assumes 20 GB, which is $100.46 a month.

| Change orders a month | Low use, 1 GB | **Starting plan: expected use, 1 GB** | Worst case: high use, 20 GB |
| ---: | --- | --- | --- |
| 50 | 0.54 + 0.05 + 5.02 = $5.61 | 2.19 + 0.08 + 5.02 = **$7.29** | 14.75 + 0.15 + 100.46 = $115.36 |
| 200 | 2.18 + 0.20 + 5.02 = $7.40 | 8.78 + 0.30 + 5.02 = **$14.10** | 59.00 + 0.60 + 100.46 = $160.06 |
| 1,000 | 10.89 + 1.00 + 5.02 = $16.91 | 43.89 + 1.50 + 5.02 = **$50.41** | 295.02 + 3.00 + 100.46 = $398.48 |

As data grows, add $5.02 a month for each extra GB. At 5 GB that is 4 × 5.02 = $20.08 more.

Not included: hosting for the app's API, logging, photo storage, tax, and people's time.

### Who pays

AWS credits pay up to $100, then Cohyric pays the bill. On Nov 13, 2026 the credits had 151 days left, so they expire around Apr 13, 2027. That is 151 ÷ 30.4 = 4.97 months. Cohyric starts paying when the $100 runs out or the credits expire, whichever comes first. The table uses the starting plan.

| Change orders a month | Monthly total | Months until $100 runs out | Which comes first | Credit used |
| ---: | ---: | --- | --- | --- |
| 50 | $7.29 | 100 ÷ 7.29 = 13.7 | Expiry, at 4.97 months | 7.29 × 4.97 = $36.23 |
| 200 | $14.10 | 100 ÷ 14.10 = 7.1 | Expiry, at 4.97 months | 14.10 × 4.97 = $70.08 |
| 1,000 | $50.41 | 100 ÷ 50.41 = 2.0 | The $100, at 2.0 months | $100.00 |

At 50 or 200 change orders a month, part of the credit goes unused. The proof of concept and the model comparison in section 4 are best run before Apr 13, 2027, while the credits pay for them.

**The credits cover Claude.** AWS's general credit terms exclude AWS Marketplace charges unless AWS authorizes them [8], and Claude models are billed through Marketplace [4][5]. Bona checked our credit on Nov 13, 2026: it applies to Amazon Bedrock, Amazon Bedrock AgentCore and Amazon SageMaker AI, and Claude through Bedrock is covered.

Two small limits remain. S3 is not on that list, so the S3 file storage, about 2 cents a month per GB, would be billed to Cohyric from the start. Credits do not pay tax [8].

## 4. Model choice

All three are in the Bedrock catalog. Prices are the "Geo and in-region" rates, which keep Tad's data on US servers as decided, and are the same in N. Virginia and Oregon [1]. The last two columns use the expected case from section 2.

| Model | Input per 1M | Output per 1M | Per change order | 1,000 a month |
| --- | ---: | ---: | ---: | ---: |
| Claude Haiku 5.5 (small, fast) | $0.11 | $0.55 | $0.0022 | $2.19 |
| Amazon Nova Pro | $0.80 | $3.20 | $0.0150 | $15.00 |
| **Claude Sonnet 5.5 (recommended)** | **$2.20** | **$11.00** | **$0.0439** | **$43.89** |

Example for Haiku 5.5: 13,950 × 0.11 ÷ 1M + 1,200 × 0.55 ÷ 1M = $0.00153 + $0.00066 = $0.0022.

**Recommendation: Claude Sonnet 5.5.** Con's point is that estimate accuracy decides whether subcontractors get paid, and the price gap between the cheapest and the dearest model here is small: about $42 a month at 1,000 change orders in the expected case (43.89 − 2.19), and about $280 in the high case (295.02 − 14.75). AWS describes Sonnet 5.5 as built for knowledge work [5] and Haiku 5.5 as built for high-volume, speed-sensitive work [4]; our job is low-volume and accuracy-sensitive. This is a choice on fit and price, not on test results. No model has been tested on Tad's data yet. The proof of concept should run the same change orders through Haiku 5.5 as well. If the estimator cannot tell the answers apart, switching cuts the model cost by 95%.

## 5. Knowledge-base costs that are not per token

Recommended: the **Bedrock Managed Knowledge Base**, which reads documents straight from S3 [1].

| Line item | Price | Source |
| --- | --- | --- |
| Index storage | $5.00 per GB of raw data per month | [1] |
| Reading and indexing documents (parsing, embedding) | $0 | [1] |
| Each lookup (Retrieve call) | $1.00 per 1,000 | [1] |
| Re-ranking results with the built-in ranker | $0 | [1] |
| The source files in S3 Standard | $0.023 per GB per month | [2] |

Not verified: whether index storage is billed for part of a GB or rounded up. The budget assumes a whole GB at minimum.

If we build the knowledge base ourselves instead (self-managed), the pieces are priced separately:

| Line item | Price | What it means for us |
| --- | --- | --- |
| Embedding with Titan Text Embeddings V2 [1] | $0.02 per 1M tokens, one time | 30M tokens of documents × $0.02 = $0.60 |
| Vector store: S3 Vectors [2][7] | $0.06 per GB per month, $0.20 per GB uploaded, $0.0025 per 1,000 queries | Cents a month at our size |
| Vector store: OpenSearch Serverless, classic [3][7] | $0.24 per unit-hour, minimum 2 units (1 for dev-test) | 2 × $0.24 × 730 hours = **$350.40 a month**, or $175.20 for dev-test, even when idle. Avoid |

## 6. The two data tiers

| Tier | What Tad sends | What it is for | AI cost |
| --- | --- | --- | --- |
| Minimum (proof of concept) | A handful of original proposals with their change orders: request, final proposal, revisions, approval, final amounts, dates | Show that the AI flags out-of-scope work correctly and lands in the right cost range, and measure real token counts | Under 1 GB: about $5 a month plus cents per test run |
| Full ("full training") | Many more of the same, plus cost breakdowns: labor hours and rates, materials, equipment, quotes, permits, overhead, markup, tax | Estimates accurate enough for the estimator to rely on | Grows with the data: $5.02 a month per GB, so 5 GB is about $25 a month |

We start with the minimum tier and add data as needed.

"Training" here means loading the documents into the knowledge base so the model can look them up. It does not mean retraining the model (fine-tuning). The spec leaves that open and proposes starting with the knowledge base. Fine-tuning is priced differently: for Amazon Nova Pro it is $0.008 per 1,000 training tokens plus $1.95 a month to store the model [1], so 30M tokens over 3 passes would be 90,000 × $0.008 = $720 one time. A fine-tuning price for the Claude 5.5 models is not verified: none is listed on the pricing page [1].

## 7. What would change the answer

- **Real document sizes.** The original proposal is the largest input. If Tad's proposals run 25 pages instead of 6, input per run goes from 9,300 to 22,600 tokens. Measure this in the proof of concept.
- **Re-runs.** Every re-ask after an edit is another full run.
- **Data volume.** Storage is about $5.02 per GB per month. At 1 GB it is most of the bill at 50 change orders a month; above that the model is.
- **The model.** Haiku 5.5 is 5% of Sonnet's model cost. One tier up, Claude Opus 5.5 at $4.40 and $22.00 [1], is double.
- **The vector store.** Classic OpenSearch Serverless would add $175 to $350 a month of fixed cost.
- **Fine-tuning instead of lookup**, or **sending photos to the AI**. Both are outside this budget and the spec excludes photos for now.
- **Routing.** Decided: US servers only. Worldwide routing would be about 10% cheaper ($2.00 and $10.00 for Sonnet 5.5 [1]) but is ruled out because Tad's data would leave the US.
- **Very long prompts on Haiku 5.5.** Above 100,000 input tokens the price is five times higher [1][4]. Our high case is 29,700.
- **How we pay.** The $100 of AWS credits covers Bedrock, including Claude. Cohyric starts paying when the credits expire around Apr 13, 2027, or after about two months if volume is near 1,000 change orders a month. See [Who pays](#who-pays).
- **Price changes.** AWS changed a Sonnet 5.5 rate as recently as Oct 7, 2026 [1]. Re-check before committing a budget.

## Not verified

- Every token count in section 2. They are assumptions until we have Tad's documents.
- The Nov 4 price figures. They do not match any text model on the pricing page.
- Whether Claude's reasoning is billed as output tokens.
- Whether knowledge-base index storage is rounded up to a whole GB.
- A fine-tuning price for Claude 5.5 models.
- The 1.5 runs per change order. Agreed as the working figure until tested on Tad's data.
- That the Managed Knowledge Base is offered in the region we will use. The pricing page does not list regions for it.

## Sources

Sources 1 to 7 read Nov 11, 2026. Source 8 read Nov 13, 2026.

1. Amazon Bedrock pricing: https://aws.amazon.com/bedrock/pricing/ (model prices, Titan embeddings, Managed Knowledge Base, Nova fine-tuning)
2. Amazon S3 pricing: https://aws.amazon.com/s3/pricing/ (S3 Standard storage, S3 Vectors)
3. Amazon OpenSearch Service pricing: https://aws.amazon.com/opensearch-service/pricing/ (OpenSearch Serverless)
4. Claude Haiku 5.5 model card: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html
5. Claude Sonnet 5.5 model card: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html
6. Knowledge base chunking: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html
7. Knowledge base vector stores: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-setup.html
8. AWS Promotional Credit terms (last updated Sep 24, 2026): https://aws.amazon.com/awscredits/

How the prices were read: the pricing pages fill in their Amazon, Anthropic, S3 and OpenSearch tables in the browser from AWS's own price files (under `https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/`). I downloaded the pages and those files and matched them up for US East (N. Virginia), and for US West (Oregon) on the Bedrock page. Both regions gave the same model prices. On Nov 13, 2026 Bona compared the three model rows in section 4 (Claude Haiku 5.5, Amazon Nova Pro, Claude Sonnet 5.5) with the pricing page in a browser, and all three matched.
