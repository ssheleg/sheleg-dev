# Skill Card — sheleg-dev

## Identity

| Field | Value |
|---|---|
| Pack | `sheleg-dev` |
| Version | `0.11.4` |
| Skills | `stripe-billing`, `crypto-payments`, `error-tracking`, `ad-tracking`, `google-signin`, `google-auth`, `frontend-performance` |
| License | MIT |
| Source | https://github.com/ssheleg/sheleg-dev |

## Job and boundary

Wire the integration seams under a paid product: money, measurement, Google
identity, error tracking and frontend performance. The pack does not choose
prices, decide product behavior, draw checkout screens or write their copy.

## Inputs and outputs

Inputs are an existing product, provider configuration and the relevant user
flow. Outputs are repository changes, migrations, webhook handlers, event
contracts, tests and verification evidence. No provider secret ships with the
pack.

## Runtime and trust

Implementation may contact Stripe, payment networks, advertising APIs, Google
or Sentry only within the user-authorized integration. Credentials stay in the
product's secret store. Payment authority belongs to verified provider events,
not browser redirects; duplicate delivery is expected and tested.

## Distribution

Install from npm/GitHub, through the Agent Skills CLI, or as the
`sheleg-dev` Claude Code plugin.

## Verification

- Repository validator: `python3 test/validate.py`
- Integration invariants and negative plants: repository test suite
- House audit: pinned `make-skill` auditor in `validate.yml`
- Behavioral data: `test/evals/`
- Evaluation status: authored, schema-validated, never run against a model

## Known limits

The skills provide implementation contracts, not provider accounts, business
pricing or legal advice. Provider APIs and consent rules change; a production
integration must verify the current official contract before release.

