# FW03 — bounded credential and citation repair

As of 2026-10-13. Owner: sheleg-dev. Branch: `fix/fw03-credential-boundaries`.
Baseline: [`f946ce6`](https://github.com/ssheleg/sheleg-dev/tree/f946ce6625ae8458b6963e9c2a9fe29b4c642bdd).
This is implementation evidence, not provider, native-host or release acceptance.

## Requirement mapping

| Row | Recovered defect and delivered scope | Acceptance / residual |
|---|---|---|
| B-82 | Payload Markdown was outside the repository citation check. `skill_repo_path_gaps` and `check_skill_repo_paths` in `test/validate.py` now check explicit `plugins/`, `test/`, `bin/`, `scripts/` prefixes exactly, including end-of-file citations; no basename fallback. Consumer project paths stay outside this rule. | Focused positive/negative controls and actual public-validator plant pass. Bare or consumer-project paths are not claimed validated. |
| B-86 | Stripe prescribed a mode assertion without supplying one. `plugins/sheleg-dev/skills/stripe-billing/scripts/assert-stripe-env.mjs` now exports it; the skill calls it before client construction and `references/price-integrity.md` supplies the copy block. The validator's credential table includes this reference. | 18 local assertions cover secret/restricted keys, both mode mismatches, absent/unknown mode and unsupported key formats. Prefix agreement is not authentication or permission. |
| B-87 | The old row treats three skills alike. Current Google GIS uses a public client ID and explicitly no client secret; CAPI teaches payloads and no authenticated adapter. Google-auth does teach service-account JSON and OAuth client secrets. | Current source audited, boundaries documented in existing Google-auth and Meta references. Removed access-token logging from Google-auth SKILL.md. Meta current Test Events contract remains unverified after official page HTTP 429. No blanket closure. |
| B-91 | The shell gate knew only Heleket's named opaque credential. Add only established Google names: GOOGLE_CREDENTIALS and GOOGLE_CLIENT_SECRET. Preserve public client/project/pixel IDs and ADC configuration paths. | 12 new fixtures: 8 named-secret refusal/authorization/reader cases and 4 metadata counterexamples. Only explicit shell assignments are covered; inherited values, credential files and ambient ADC remain outside this gate. CAPI row remains open pending provider contract evidence. |
| B-90 / B-92 | Copy channels do not register hooks; live-host environment isolation has residual evidence gaps. | Unchanged and open. No real settings, provider credentials, payments or native host were used. |

The Google rule is conservative command admission, not automatic classification of
a particular principal's IAM permissions. A separately restricted test project is
still a real provider operation; offline tests use credential-free mocks. Production
category authorization is the existing gate policy, not a grant of provider rights.

## Negative controls and checks actually run

- Baseline citation probe: added an explicit missing `plugins/missing/SKILL.md:999999`
  reference to an owned source copy; the old public validator exited 0. After the
  change, the same plant in the owned worktree exited 1 with B-82, and restoring the
  exact original bytes returned exit 0. The plant is absent from delivered source.
- Before hook implementation, the expanded suite had 4 failures out of 77 because
  Google secret assignments were accepted in test runs. After implementation,
  `node test/moneygate_test.js` exits 0 with 77 fixtures.
- `python3 -B test/audit_regressions/fw03_credentials.py`: 3/3 groups pass,
  including 18 executable Stripe assertions. Uses synthetic strings only and no
  provider calls or temporary source trees. Reader-project path and metadata
  positives prevent indiscriminate refusal.
- `python3 -B test/validate.py`: exit 0, 28 checks, 7 skills, v0.13.3. Routed
  triggers are explicitly **unlooked** in this standalone worktree; no umbrella
  discovery result is claimed.
- `npm test`: exit 0. Structural 28; money-gate 77; money fixtures 16; installer
  11 cases; all 44 audit regression scripts. Counts describe their own layers and
  are not summed into one homogeneous test total.
- `git diff --check`: exit 0. Security payload counts and Stripe body measurements
  updated from the validator: 62 plugin files, 68 package files, 4552 body tokens,
  399 body lines. Version and release surfaces remain v0.13.3.

## Provider evidence, checked 2026-10-13

- [Stripe API keys](https://docs.stripe.com/keys): sandbox/live secret and restricted
  prefixes. Organization and unknown formats fail closed in the shipped assertion;
  webhook signing secrets are a different credential.
- [Google ADC](https://docs.cloud.google.com/docs/authentication/application-default-credentials):
  environment path, local ADC file, then attached identity; the path can identify a
  federation configuration or service-account key, so its name alone is not a secret.
- [Google OAuth production readiness](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview):
  Testing controls app access and token lifetime; it does not establish synthetic
  user data. Basic identity scopes have exceptions to Testing restrictions.
- [Meta official Node SDK](https://github.com/facebook/facebook-nodejs-business-sdk/blob/main/README.md):
  provider access tokens are opaque and needed by the API client. The current
  [Test Events page](https://developers.facebook.com/docs/marketing-api/conversions-api/using-the-api/#testEvents)
  returned HTTP 429, so no prefix or test-token inference became a gate rule.

## Next acceptance steps

Independent reviewer replays the bounded negative/positive corpus, reviews the actual
source diff and checks the Google/Stripe authority boundary. Parent owns integration
and release policy. No claim of zero bugs, task-quality parity, installed propagation
or provider delivery follows from this source acceptance. Investigate current CAPI
authentication semantics, then scope any remaining B-91 rule separately.

Skills used: task-pipeline for delivery; agent-sync for advisory ownership;
evidence-docs for measured claims; stripe-billing, google-auth, google-signin and
ad-tracking for source contract review. make-skill supplied construction guidance in
the preceding wave; no new skill or package release was created here.

## Current Google Testing correction and candidate CI

The reviewed Google app-state source also contradicted four current owner claims:
Google-signin entry setup/troubleshooting and the corresponding full-guide rows
said Testing always needs allowlisting or instructed publishing as the remedy.
Both now explain the basic identity scope exception and Workspace restrictions.
No provider configuration is changed. Structural validation remains the gate for
these prose changes; no invented model or login test is claimed.

The owner validate workflow now follows the standing policy: nightly 23:00
Europe/Warsaw, reusable release call, manual diagnostics, and only a deliberate
ready_for_review PR promotion. Job bodies are unchanged; opened/synchronize/push
are absent. A successful manual dispatch is not eligible PR admission, per
[GitHub required checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#checks-from-some-workflow-jobs-are-not-evaluated).
The operator policy explicitly permits manual hosted CI for an urgent or explicit
candidate; promotion is that bounded exception, not continuous per-push CI.

Independent review identified three holes in the initial B-82 tokenizer: `.mjs`
was ignored, line zero was treated as no citation, and only the first endpoint of
a range was checked. Added `.mjs`/`.cjs` recognition and opt-in full range parsing
for payload checks, preserving the older callers' interface. The added missing
module control failed before the fix; zero, reversed and out-of-bounds ranges
now fail, while valid single/range module citations pass.

After the review fixes, a positive structural baseline exited 0 before
`python3 -B test/negatives.py` ran: all 48 existing workflow guards rejected
their plants. This sequencing prevents an unrelated baseline failure from
being mistaken for a successful negative control.
