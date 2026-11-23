# Hosting decision (B12)

**Recommendation:** run the API on **Render** as a paid, always-on web service (Starter, about $7 a month, US region), and serve the web build from **Cloudflare Pages** (free, static files, no sleeping server). Both deploy from GitHub, keep secrets in their own settings, and give an HTTPS address a phone off the club's Wi-Fi can open. The one cost is the API: a free API tier sleeps, and a sleeping API can fail a partner demo, so the API must be on a paid always-on plan. **Fallback:** the API on **Fly.io** (always-on from about $2.19 a month, deploys through a GitHub Action) and the web build on **Netlify Free**.

Every price and limit below was read from the provider's official page on **2026-11-23** (the URL is next to it). Anything I could not confirm is marked NOT VERIFIED and repeated in "Not verified" at the end. Prices change, so re-check the pricing page on the day an account is created.

## What the app needs from a host

- API: FastAPI on Python 3.12, always on, HTTPS, health check at `/health`, outbound connections to the Supabase session pooler (port 5432), to Resend (HTTPS) and to Amazon Bedrock in a US region.
- Web: static files from `expo export --platform web` (`app.json` sets `web.output` to `static`), including the `/approve?token=...` page, which must still open after a refresh.
- US regions only, free or low cost, deploy from GitHub, secrets only in the host's secret settings.
- The club's $100 AWS credit is not used for hosting. The AWS free page says the credits apply to "select services" and does not list Lightsail (https://aws.amazon.com/free/), so this document does not rely on it.

## Option 1: API host

| | **Render** (recommended) | Fly.io (fallback) | Railway | AWS Lightsail containers | AWS App Runner |
| --- | --- | --- | --- | --- | --- |
| Cheapest always-on | Starter, 0.5 CPU / 512 MB, **$7/month** (see note 1) | Machine `shared-cpu-1x` 256 MB **$2.19/month**; 512 MB **$3.69/month** | Hobby **$5/month** including $5 of usage credit; usage billed at $10/GB RAM and $20/vCPU per month | Nano **$7/month**, 0.25 vCPU, 512 MB | Not available to new accounts |
| Free tier | Free web service, 0.1 CPU / 512 MB, 750 free hours a month | $1 credit with no card (expires after 7 days); $5 of usage a month with a card | $0 with $1 of monthly credit; 0 custom domains | "Free Tier" mentioned, amount and length not stated | n/a |
| Sleep / cold start | **Free:** spins down after 15 minutes without traffic, wake-up "about one minute". **Paid:** the spin-down rule is written only for Free services | Optional: scale to zero is a setting, cold start "about 2 seconds or more". Leave `min_machines_running` at 1 for a demo | **Free:** sleeps after 5 to 10 minutes. **Hobby and up:** always-on | No sleep feature; charged whether enabled or disabled | n/a |
| US regions | Oregon, Ohio, Virginia (chosen when the service is created; cannot be changed later) | Ashburn VA, Secaucus NJ, Dallas, Los Angeles, Chicago, San Jose | US West (California), US East (Virginia) | Lightsail US regions: N. Virginia, Ohio, Oregon (container-specific list NOT VERIFIED) | n/a |
| Custom domain + HTTPS | Yes, managed TLS, auto-renewed; free default `onrender.com` address | Yes, Let's Encrypt; first 10 certificates per organization free | Yes on Hobby (2 domains), Let's Encrypt, auto-renewed; free `up.railway.app` address | Default address is HTTPS; custom domain needs a manually requested and validated certificate | n/a |
| Deploy from GitHub | Yes: link a repo and branch, auto-deploy on commit or after CI passes, "Root Directory" setting for the `backend` folder | No built-in link found; documented route is a GitHub Action running `flyctl deploy` with a token | Yes: auto-deploy from a linked branch, "Root Directory" setting | No. You build a container image and push it | Closed to new customers |
| Secrets | Environment variables and secret files in the dashboard; groups can be shared across services | `fly secrets set`, encrypted, values cannot be read back | Variables per service; "sealed" variables are never shown again | Plain environment variables per deployment; no secret store documented | n/a |
| Health check | Yes: HTTP path, 2xx/3xx within 5 seconds; a deploy that is not healthy within 15 minutes is cancelled | Yes: `http_service.checks` in `fly.toml` | Yes: path, waits for 2xx, default 300 seconds; checked at deploy only | Yes: per endpoint, 2 to 60 s timeout | n/a |
| Rollback | Dashboard "Rollback" to a previous deploy; Free keeps the last 2 | `fly deploy --image <earlier image>`; old images may be pruned | Three-dot menu on a previous deployment restores image and variables | New deployment from any of the last 50 saved versions | n/a |
| Needs Docker | No (uses a Python runtime; set `PYTHON_VERSION`) | A Dockerfile is generated for FastAPI; whether local Docker is needed NOT VERIFIED | Not required (Railpack builder); Python 3.12 NOT VERIFIED | Yes, to build and push images | n/a |
| Card required | NOT VERIFIED | Pricing page says a card is on file for all organizations; free-plan page says the $1 credit needs none (the two pages disagree) | Free and Trial: no card; Hobby: a card | NOT VERIFIED | n/a |

**Note 1, Render price.** Render's own pricing page did not return plan prices when fetched, and its compute-plans page lists specs only. The $7 figure (and $25 for Standard, 1 CPU / 2 GB) comes from a search result that quotes https://render.com/pricing. Treat it as likely correct and confirm it when the account is created.

**Sources (all read 2026-11-23):**
- Render: https://render.com/docs/free, https://render.com/docs/compute-plans, https://render.com/docs/regions, https://render.com/docs/health-checks, https://render.com/docs/rollbacks, https://render.com/docs/deploys, https://render.com/docs/monorepo-support, https://render.com/docs/language-support, https://render.com/docs/custom-domains, https://render.com/docs/configure-environment-variables, https://render.com/pricing
- Fly.io: https://docs.fly.io/about/pricing, https://docs.fly.io/about/free-plan, https://docs.fly.io/launch/autostop-autostart, https://docs.fly.io/reference/regions, https://docs.fly.io/apps/secrets, https://docs.fly.io/blueprints/rollback-guide, https://docs.fly.io/launch/continuous-deployment-with-github-actions, https://docs.fly.io/networking/custom-domain
- Railway: https://railway.com/pricing, https://docs.railway.com/deployments/regions, https://docs.railway.com/deployments/healthchecks, https://docs.railway.com/deployments/deployment-actions, https://docs.railway.com/deployments/github-autodeploys, https://docs.railway.com/variables, https://docs.railway.com/networking/domains/working-with-domains, https://docs.railway.com/networking/outbound-networking
- AWS: https://aws.amazon.com/lightsail/pricing/, https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html, https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html, https://aws.amazon.com/free/

**Why Render.** Of the options with a documented always-on paid plan, it has the simplest setup with no Docker and no GitHub Action: link the repo, set the `backend` folder, set `PYTHON_VERSION`, add secrets, set the health path to `/health`. Its health check, rollback, managed HTTPS and US regions are all documented. Its cost is $7 a month for one always-on service. Free would be $0, but it sleeps for about a minute after 15 idle minutes, and Render's free page also lists "accessing an external database" as traffic that can get a Free service suspended, which is what this API does.

**Why not the others.**
- *Fly.io* is cheaper and fully documented for secrets and rollback, but it needs a GitHub Action and a deploy token, and its pages disagree on whether a card is needed. It is the fallback.
- *Railway* works, but its free tier sleeps and its usage-based billing is harder to predict. Python 3.12 and outbound port 5432 are not confirmed on its pages.
- *Lightsail* has no GitHub deploy, needs Docker, and needs a manual certificate for a custom domain.
- *App Runner* is closed: "AWS App Runner is no longer open to new customers" (https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html).

## Option 2: Web build host

| | **Cloudflare Pages** (recommended) | Netlify Free (fallback) | Vercel Hobby | EAS Hosting (Expo) |
| --- | --- | --- | --- | --- |
| Cost | **$0.** Static asset requests are "free and unlimited" | $0 with 300 credits a month; paid Personal $9, Pro $20 | $0; Pro $20 per seat | Free plan: 100,000 requests, 1 GB storage a month; Starter $19/month + usage |
| Over the limit | Not an issue for static files | All projects on the account are **paused** until the next billing cycle (no overage charge) | Hard stop at the cap, wait 30 days | NOT VERIFIED |
| Sleep / cold start | Static files from a CDN; none described | Static files from a CDN; none described | Static files; none described | Not described |
| US region | Global CDN; no region setting found (NOT VERIFIED for "US only") | Global CDN; no region setting found | Global; no static region setting found | Runs on Cloudflare; no region setting found |
| Custom domain | Yes; apex domain needs the DNS zone on Cloudflare, a subdomain needs only a CNAME. Free default `pages.dev` address. Automatic SSL not stated on the domain page | Yes, free HTTPS with auto-renewal | Yes, 50 per project | **Not on Free**; paid plan, 1 per project |
| Deploy from GitHub | Yes, GitHub App; org or personal repos; root directory, build command and output directory settings; max 5 Pages projects per repo | Yes; base/package directory, build command and publish directory | Yes; Root Directory, build command override, output directory. **Hobby cannot connect repos owned by a Git organization** | Via Expo Workflows (`.eas/workflows`) or `eas deploy` from a laptop |
| Build env vars | Dashboard, Settings, Environment variables; encryption NOT VERIFIED | Dashboard, CLI or API | Encrypted at rest; per environment | `.env` at export time |
| SPA / deep-link fallback | **Documented:** with no top-level `404.html`, Pages treats the site as a single-page app and serves the root for unknown paths | **Documented:** `/*  /index.html  200` in `_redirects` | `vercel.json` rewrite (from a summary of the page) | **NOT VERIFIED** for Expo's `single` output |
| Rollback | Dashboard, "Rollback to this deployment", instant; deployments kept 30 days plus the 100 most recent | "Publish Deploy" on an earlier deploy, instant, no credits | Instant rollback; **Hobby only to the immediately previous deployment** | `eas deploy:alias --prod --id=<deploymentId>`, instant |
| Blockers | Cloudflare says new projects should start on Workers static assets; Pages is not deprecated | Private organization repos are Pro only (this repo is public, so not a blocker) | Terms: Hobby is "only for your personal or non-commercial use" | No custom domain on Free; SPA fallback unconfirmed |

**Sources (all read 2026-11-23):**
- Cloudflare: https://developers.cloudflare.com/pages/, https://developers.cloudflare.com/pages/platform/limits/, https://developers.cloudflare.com/pages/configuration/serving-pages/, https://developers.cloudflare.com/pages/configuration/build-configuration/, https://developers.cloudflare.com/pages/configuration/build-image/, https://developers.cloudflare.com/pages/configuration/monorepos/, https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/, https://developers.cloudflare.com/pages/configuration/custom-domains/, https://developers.cloudflare.com/pages/configuration/rollbacks/, https://developers.cloudflare.com/pages/functions/pricing/, https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/
- Netlify: https://www.netlify.com/pricing, https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/, https://docs.netlify.com/build/configure-builds/monorepos.md, https://docs.netlify.com/deploy/manage-deploys/manage-deploys-overview.md, https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/billing-faq-for-credit-based-plans.md, https://docs.netlify.com/manage/domains/secure-domains-with-https/https-ssl.md
- Vercel: https://vercel.com/pricing, https://vercel.com/docs/limits, https://vercel.com/docs/plans/hobby, https://vercel.com/docs/instant-rollback, https://vercel.com/docs/builds/configure-a-build, https://vercel.com/docs/environment-variables, https://vercel.com/legal/terms (Section 4)
- Expo: https://expo.dev/pricing, https://docs.expo.dev/eas/hosting/get-started.md, https://docs.expo.dev/eas/hosting/deployments-and-aliases.md, https://docs.expo.dev/eas/hosting/custom-domain.md, https://docs.expo.dev/eas/hosting/workflows.md, https://docs.expo.dev/router/reference/redirects.md

**Why Cloudflare Pages.** It costs nothing for static files, it documents the single-page fallback explicitly, it supports GitHub repos with a root-directory setting (the build lives in `frontend/`), and a rollback is one click. A static host has no server to put to sleep, so the web build cannot fail a demo the way a free API can. Vercel Hobby is limited to personal or non-commercial use by its terms, and ChangeOrder is a product for a company, so avoid it. Netlify is a good fallback, but a Free account that uses up its credits pauses every site on it. EAS Hosting's fallback for deep links is not documented, and a custom domain needs a paid plan.

**Cloudflare Pages vs Workers.** Cloudflare's docs say "Start new projects with Workers". Pages still works and is the simpler path for this team. If the Pages dashboard ever blocks a new project, the Workers static-assets route needs `not_found_handling = "single-page-application"` (https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/); that is a code change for U11, not part of this decision.

## Cost summary

| Item | Recommended | Fallback |
| --- | --- | --- |
| API | Render Starter, about $7/month | Fly.io, about $2.19 to $3.69/month |
| Web build | Cloudflare Pages, $0 | Netlify Free, $0 |
| Total hosting | **about $7/month** | **about $2 to $4/month** |
| Already running, not new | Supabase (database, sign-in), Resend (email) | same |
| Bedrock | Pay per use; covered by the club's credit for Bedrock only | same |

## Settings each service needs (names only, no values)

**API service (Render).** Put every one of these in Render's environment settings (secret files are available at `/etc/secrets/<name>` if ever needed). Never commit them.

| Name | Secret? | Notes |
| --- | --- | --- |
| `PYTHON_VERSION` | no | Pin to 3.12 (Render documents this variable or a `.python-version` file; 3.12 itself NOT VERIFIED) |
| `WORKSPACE_BACKEND` | no | `postgres` in production (the SQLite fallback lives on a disk that is wiped on every deploy) |
| `WORKSPACE_COMPANY_ID` | no | Company the demo data belongs to |
| `DATABASE_URL` | **yes** | The Supabase **session pooler** string, port 5432 |
| `SUPABASE_URL` | no | Used to verify sign-in tokens |
| `SUPABASE_JWKS_URL`, `SUPABASE_JWT_AUDIENCE` | no | Optional, leave unset unless Supabase changes |
| `SUPABASE_JWT_SECRET` | **yes** | Leave unset on this project (ES256 public keys). Only for legacy projects |
| `EMAIL_API_KEY` | **yes** | Resend key |
| `EMAIL_API_URL`, `EMAIL_FROM` | no | |
| `GC_EMAIL` | no | Prototype recipient until the user table exists |
| `APP_URL` | no | See below |
| `CORS_ORIGINS` | no | See below |
| `AWS_REGION`, `BEDROCK_MODEL_ID` | no | A US region only |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | **yes** | Standard names the AWS library reads. Use a dedicated IAM user that can call Bedrock and nothing else. Hosts outside AWS cannot use an IAM role |

Also set in the service settings (not secrets): root directory `backend`, build command `pip install -r requirements.txt`, start command `python -m uvicorn main:app --host 0.0.0.0 --port <the port Render provides>` (confirm the port variable name when creating the service; NOT VERIFIED here), health check path `/health`.

The Supabase service-role key and AWS keys are backend-only and must never be placed in a variable starting with `EXPO_PUBLIC_`.

**Web build (Cloudflare Pages).** These are inlined into the public JavaScript bundle at build time, so they are public by design (https://docs.expo.dev/eas/environment-variables/usage.md). Only public values belong here.

| Name | Notes |
| --- | --- |
| `EXPO_PUBLIC_API_URL` | The hosted API address, `https://...`, no trailing slash |
| `EXPO_PUBLIC_SUPABASE_URL` | Public project address |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | The public (publishable) key only |
| `NODE_VERSION` | Optional pin; Pages defaults to Node 22 on its v3 build image |

Build settings: root directory `frontend`, build command `npx expo export --platform web`, output directory `dist`.

## How the three addresses must be set

The order matters because each depends on another's final address.

1. Create the Cloudflare Pages project first, **without** a custom domain, to learn its `https://<project>.pages.dev` address. (Or decide a custom domain first and use it from the start; changing it later means changing all three settings.)
2. Create the Render service and note its `https://<service>.onrender.com` address.
3. Set, in this order:
   - `EXPO_PUBLIC_API_URL` (Pages) = the Render address. Must be `https`. A phone off the club's Wi-Fi cannot reach a LAN address like the ones in the example env files.
   - `APP_URL` (Render) = the Pages address, with no trailing slash. This is the base of the link in the emailed message (`/approve?token=...`), so it must be the public address, not `localhost`.
   - `CORS_ORIGINS` (Render) = the Pages address, exactly as the browser shows it (scheme and host, no path, no trailing slash). Several origins are separated by commas. Add the custom domain too if one is used, and keep local origins only for local `.env` files, not the host.
4. Re-run the Pages build after changing any `EXPO_PUBLIC_*` value, because they are fixed at build time. Changing a Render variable restarts the API; changing a Pages variable does nothing until the next build.

## Deploy steps

**API on Render** (J11 does this, with the account owner's approval).
1. Create a Render account and a Web Service from the GitHub repo. Region: Virginia or Ohio (the same side of the country as the Supabase project if it is in the east; check the project's region first). Plan: Starter.
2. Settings: root directory `backend`, runtime Python, `PYTHON_VERSION` 3.12, build and start commands as above, health check path `/health`, auto-deploy "After CI Checks Pass" on branch `main`.
3. Add the secrets from the table above.
4. Deploy, open `https://<service>.onrender.com/health`, and confirm `{"status":"ok"}`.
5. Sign in with each of the three test accounts from the hosted web build.
6. Open an emailed GC link from a phone on mobile data.

**Web on Cloudflare Pages** (U11 does this).
1. Create a Pages project, connect the GitHub repo (install the Cloudflare GitHub App on the repo's owner and select only this repository).
2. Set root directory `frontend`, build command and output directory as above, and the `EXPO_PUBLIC_*` variables.
3. Do **not** add a top-level `404.html`; its presence turns off the single-page fallback.
4. After the first deploy, open `<pages address>/approve?token=test` and **refresh** it. The page must load, not 404. Because `app.json` currently sets `web.output` to `static`, Expo writes one HTML file per page; confirm `/approve` resolves to the right file on Pages, and if it does not, ask Uriel to switch the export to `single` output.

## Rollback

- **API:** Render dashboard, Deploys, pick the last good deploy, "Rollback to this deploy". The dashboard rollback turns off auto-deploy, so switch it back on afterwards. Disks and database changes are not rolled back, so a migration must be reversed by a new migration (Bona). Render keeps rollback targets "based on your workspace plan"; on Free only the last two.
- **Web:** Cloudflare Pages dashboard, Deployments, All deployments, the three-dot menu, "Rollback to this deployment". Instant. Preview deployments cannot be a target, and deployments older than 30 days are deleted unless they are among the latest 100.
- **Fallback hosts:** Fly.io `fly deploy --image <earlier image>`; Netlify "Publish Deploy" on an earlier deploy.

## Who holds the accounts, and what Bona must decide

Recommended holders (to be confirmed by Bona):

| Account | Holder | Why |
| --- | --- | --- |
| Render | Bona | Bona already owns the Supabase project, migrations and secrets, and the bill is about $7 a month. Jalen's work reaches production by merging to `main`; he does not need a login. Whether Render lets a second person into a Hobby workspace was NOT VERIFIED |
| Cloudflare | Bona, with Uriel invited if Cloudflare allows it on a free account (NOT VERIFIED) | Uriel owns the web build; a failed build needs someone who can open the project |
| Resend, Supabase, AWS | Unchanged (Bona) | Not part of this decision |
| Payment card | One card, held by the club or Bona | Render needs a card for a paid plan; no personal card of a student should be tied to the club's production unless agreed |

Decisions for Bona:
1. Approve Render Starter at about $7 a month, or choose the Fly.io fallback at about $2 to $4.
2. Which card and which email address own the accounts, and whether a club or shared mailbox is better than a personal address, so access survives a change of team.
3. Whether to buy a custom domain. It is not needed for the demo (`onrender.com` and `pages.dev` are both HTTPS), but a shorter address in the GC's email looks more trustworthy. It costs money and an apex domain on Cloudflare means moving its DNS to Cloudflare.
4. When to turn the API plan on and off. Render's paid instances are billed by the second per the search snippet (NOT VERIFIED on an official page), so the service could run only around demos, but a service that is off is exactly the failure to avoid. Recommended: leave it on.
5. Whether the AWS keys for Bedrock may sit in Render's settings (a dedicated IAM user limited to Bedrock) or Bedrock calls should wait until there is a better route.
6. Whether to ask Uriel for a `single` web export if the `/approve` refresh test fails.

## Risks and things to check before the demo

- **Database from Render to Supabase (port 5432).** Nothing on Render's pages blocks it, but they do not say it is allowed either. Test it once on a paid service before relying on it. If it fails, ask Bona before changing anything.
- **Files on the API's disk.** Render's filesystem is wiped at every deploy, restart and spin-down, so photos saved in `backend/uploads` and the SQLite fallback would disappear. Keep `WORKSPACE_BACKEND=postgres` and put photos in private storage (task B11, J9).
- **Outbound email.** Free Render services cannot use ports 25, 465 or 587; Resend over HTTPS is unaffected, and the paid plan is the recommendation anyway.
- **A secret in the web bundle.** Anything in a variable starting with `EXPO_PUBLIC_` is readable by anyone. Only the public Supabase key and the API address go there.
- **Render region.** It cannot be changed after the service is created, so choose it carefully.
- **Cloudflare's note.** New projects are pointed to Workers; revisit if Pages shows a deprecation date.

## Not verified

- Render's Starter price ($7) and Standard ($25): the pricing page did not return prices when fetched; the figure comes from a search result quoting it. Whether paid instances are billed by the second: same source.
- Render: Python 3.12 is not listed on the page read (the pin mechanism is); which variable carries the port; whether a card is needed; whether outbound port 5432 is allowed; whether a second person can join a Hobby workspace.
- Fly.io: whether a card is needed (the pricing page and the free-plan page disagree); whether outbound port 5432 is allowed; whether local Docker is needed; Python 3.12.
- Railway: Python 3.12; outbound 5432; cold-start time; secret files; retention for rollbacks.
- Lightsail: free-trial amount; container regions; automatic certificate renewal; credit eligibility; card requirement.
- AWS $100 credit: the statement in the brief that it covers only Bedrock, AgentCore and SageMaker AI was not found on aws.amazon.com/free/, which lists the Free plan as limited to "select services". Treat the brief as the club's rule and do not assume other services are covered.
- Bedrock access from outside AWS without static keys (an IAM role): not documented on any page read.
- Cloudflare Pages: a US-only guarantee for static files; automatic SSL on custom domains; whether private repos work with the GitHub App; encryption of dashboard variables; paid Pages price; Node version setting for Workers Builds.
- Vercel: whether Hobby accepts a private personal repo; Expo variable exposure on Vercel's own pages (Expo's page covers it).
- Netlify: private personal repos on Free; its environment variable page; region choice.
- EAS Hosting: single-page fallback for `single` output, cold starts, region, what happens at the free limit, monorepo support, Node version.
- The `/approve` refresh behaviour on Cloudflare Pages for Expo's `static` output has not been tried. It has to be tested after the first deploy.
- No account was created and nothing was deployed or tested; this is a paper decision from official pages.
- Facts here were collected by fetching each provider's pages on 2026-11-23. Some pages summarise long documents; where a number matters (price, limits), re-read the cited page when the account is created.
