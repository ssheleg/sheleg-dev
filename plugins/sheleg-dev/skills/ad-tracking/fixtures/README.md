# Deduplication fixtures and the assertion pack

**Copy this whole directory into your repository.** It is the executable half of what
`SKILL.md` → *E-commerce* and `references/meta-linkedin.md` →
*Deduplication with the Conversions API* state in prose: the three payloads one purchase
produces, six invariants a correct emitter must hold — 12 assertions between them — and a
self-test that breaks the emitter one rule at a time so you can watch each assertion fail
on its own.

```bash
node assert-dedup-contract.mjs              # 6 invariants / 12 assertions
node assert-dedup-contract.mjs --self-test  # break one rule at a time; EACH ASSERTION must go red
```

No dependencies, no network, **no access token anywhere in this directory** — the sink
collects what would have been sent.

## Contents

- [The fixtures](#the-fixtures)
- [The assertions](#the-assertions)
- [What each mutant deletes](#what-each-mutant-deletes)
- [Why the browser side is read from the fixture](#why-the-browser-side-is-read-from-the-fixture)
- [Placeholders](#placeholders)

## The fixtures

| File | What it is |
|---|---|
| `purchase-pixel-browser.json` | the four arguments of the browser call: `fbq('track', 'Purchase', custom_data, { eventID })` |
| `purchase-capi-server.json` | the Conversions API request body the **webhook** sends for the same purchase |
| `purchase-capi-from-thank-you-page.json` | the body a thank-you-page-sourced emitter sends for a session whose charge never cleared — **the payload that must never exist**, kept so the assertion can name it |

The first two carry the same `event_id` and the byte-equal `event_name`, which is the
contract. The third is the defect, recorded rather than described: it was produced by
running the reference emitter with `webhook-sourced` removed.

## The assertions

| Assertion | What a wrong emitter does |
|---|---|
| `pixel-and-capi-carry-one-event-id` | generates an id per emission, so Meta counts one purchase twice |
| `pixel-and-capi-carry-one-event-name` | sends `Purchase` from the browser and `purchase` from the server: a shared id that deduplicates nothing |
| `no-purchase-reported-before-the-charge-cleared` | reports the purchase from the one place that cannot know the money moved |
| `the-browser-event-is-kept` | drops the browser event, losing the click id, the consent state and the session |
| `identifiers-reach-the-server-hashed` | puts the address itself in `user_data.em` |
| `the-shipped-capi-fixture-is-what-a-correct-emitter-sends` | anything that changes the body — a ratchet, so the fixtures you copy are the reference output |

## What each mutant deletes

| Rule | The code it removes | The integration that ships without it |
|---|---|---|
| `shared-event-id` | reading the id written once at session creation | `crypto.randomUUID()` at each emission |
| `exact-event-name` | the one `event_name` constant used by both sides | `'Purchase'` in the browser, a lowercased variant on the server |
| `webhook-sourced` | the gate that keeps the thank-you page from reporting | fires the conversion where the redirect lands |
| `keep-browser-event` | the pixel call | server-only, and blind to everything the browser carries |
| `hashed-identifiers` | the SHA-256 of the identifier | hands the raw address to the wrapper, which hashes whatever it is given |

## Why the browser side is read from the fixture

`pixel-and-capi-carry-one-event-id` and `pixel-and-capi-carry-one-event-name` compare the
server's output against `purchase-pixel-browser.json` rather than against the pixel call the
same emitter just made. That is deliberate, and it is the correction of a first pass:
reading both sides out of one emitter meant deleting `keep-browser-event` also turned those
two assertions red, so neither the id rule nor the name rule was proven on its own. Two
mechanisms that both explain a passing fixture leave both untested. The fixture is the
browser's contract, held at a boundary the server does not control.

`--self-test` fails if any rule has no fixture that isolates it, so this stays true.

## Placeholders

`usr_PLACEHOLDER_carol`, `prod_PLACEHOLDER_pro`, `fb.1.…PLACEHOLDERCLICKID`,
`203.0.113.10` (a documentation address). The email is `placeholder@example.invalid` and
the 64-hex string is its SHA-256 — a hash of a published placeholder, not of a person. No
pixel id, no dataset id and no access token appear here: the token is a runtime secret and
`references/performance-security.md` is where it belongs.
