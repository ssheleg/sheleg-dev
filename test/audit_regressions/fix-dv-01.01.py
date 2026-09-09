#!/usr/bin/env python3
"""FIX-DV-01.01 — Received vs completed state (sherlock audit, finding DV-01).

The finding: the webhook doctrine's claim (`INSERT` on a primary key) recorded
RECEIPT and was read as COMPLETION. A worker dying between the two turned the
retry into "duplicate" — a payment swallowed forever — and nothing separated a
completed row from an abandoned one.

The fix under test, in three layers:

* the doctrine (SKILL.md, references/webhook-events.md) states the split:
  a claim row carries 'processing' → 'completed', a fresh in-flight claim
  answers 5xx retry-later, an expired one is taken over, a completed one is a
  duplicate forever;
* the shipped reference handler embodies it, and its assertion pack proves the
  acceptance both ways (`crash-after-receipt-is-retryable`,
  `in-flight-claim-answers-retry-later`, `completion-is-recorded-with-the-grant`,
  `duplicate-of-completed-never-regrants`) — including `--self-test`, where each
  rule's removal is watched going red;
* the documented SQL semantics are executable: this file drives them in sqlite
  (stdlib), including the takeover race, where exactly one of two contenders
  may win the corpse.

Acceptance: crash after receipt admits a repeat worker; a duplicate of a
completed event never grants again.
"""
import os
import sqlite3
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIXTURES = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing", "fixtures")
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing", "SKILL.md")
EVENTS = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing",
                      "references", "webhook-events.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


# ------------------------------------------------------------------ the doctrine


def t_docs_state_the_split():
    skill = open(SKILL, encoding="utf-8").read()
    events = open(EVENTS, encoding="utf-8").read()
    for needle, doc, name in [
        ('claim === "completed"', skill, "SKILL.md answers duplicate by state"),
        ('claim === "in_flight"', skill, "SKILL.md answers retry-later for a fresh claim"),
        ("a claim is a receipt, not completion", skill, "SKILL.md states the split"),
        ("'processing' → 'completed'", events, "webhook-events.md names the states"),
        ("claimed_at", events, "webhook-events.md carries the claim timestamp"),
        ("died between receipt and completion", events, "webhook-events.md states the recovery"),
        ("business write committed", events, "webhook-events.md ties completion to the grant commit"),
    ]:
        assert needle in doc, f"{name}: {needle!r} is not in the document"


# --------------------------------------- the documented SQL semantics, executed


CLAIM_TTL = 300  # seconds; the docs leave the number to the reader, the shape to the test


def store():
    db = sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE processed_webhook_events (
        id           TEXT PRIMARY KEY,
        source       TEXT NOT NULL,
        state        TEXT NOT NULL DEFAULT 'processing',
        claimed_at   REAL NOT NULL,
        completed_at REAL)""")
    db.execute("CREATE TABLE grants (event_id TEXT)")
    return db


def claim(db, eid, now):
    """The documented flow: INSERT; on conflict read the state; expired → takeover."""
    try:
        db.execute("INSERT INTO processed_webhook_events (id, source, claimed_at) "
                   "VALUES (?, 'stripe', ?)", (eid, now))
        return "claimed"
    except sqlite3.IntegrityError:
        pass
    state, = db.execute("SELECT state FROM processed_webhook_events WHERE id = ?",
                        (eid,)).fetchone()
    if state == "completed":
        return "completed"
    took = db.execute(
        "UPDATE processed_webhook_events SET claimed_at = ? "
        "WHERE id = ? AND state = 'processing' AND claimed_at < ?",
        (now, eid, now - CLAIM_TTL)).rowcount
    return "claimed" if took == 1 else "in_flight"


def complete(db, eid, now):
    """The grant and the completion mark, one transaction — the documented rule."""
    with db:
        db.execute("INSERT INTO grants VALUES (?)", (eid,))
        db.execute("UPDATE processed_webhook_events SET state = 'completed', "
                   "completed_at = ? WHERE id = ?", (now, eid))


def release(db, eid):
    db.execute("DELETE FROM processed_webhook_events WHERE id = ? AND state = 'processing'",
               (eid,))


def grants(db):
    return db.execute("SELECT count(*) FROM grants").fetchone()[0]


def t_crash_after_receipt_admits_a_repeat_worker():
    db = store()
    assert claim(db, "evt_1", now=0) == "claimed"
    # the worker dies here: no complete, no release
    assert claim(db, "evt_1", now=CLAIM_TTL - 1) == "in_flight", \
        "a retry inside the window must wait, not be told duplicate"
    verdict = claim(db, "evt_1", now=CLAIM_TTL + 1)
    assert verdict == "claimed", f"the retry past the expiry was answered {verdict!r}"
    complete(db, "evt_1", now=CLAIM_TTL + 2)
    assert grants(db) == 1, "the recovered event did not grant"


def t_duplicate_of_completed_never_regrants():
    db = store()
    assert claim(db, "evt_2", now=0) == "claimed"
    complete(db, "evt_2", now=1)
    for now in (2, CLAIM_TTL + 100):  # inside the window and long past it
        verdict = claim(db, "evt_2", now=now)
        assert verdict == "completed", \
            f"a completed event answered {verdict!r} at t={now} — it would reprocess"
    assert grants(db) == 1


def t_takeover_race_has_one_winner():
    db = store()
    assert claim(db, "evt_3", now=0) == "claimed"
    # two contenders find the same corpse; the guarded UPDATE lets exactly one through
    late = CLAIM_TTL + 10
    first = claim(db, "evt_3", now=late)
    second = claim(db, "evt_3", now=late)
    assert (first, second) == ("claimed", "in_flight"), \
        f"the takeover race produced {(first, second)!r} — two workers on one event"


def t_release_on_throw_readmits_immediately():
    db = store()
    assert claim(db, "evt_4", now=0) == "claimed"
    release(db, "evt_4")  # the handler threw and answered 5xx
    assert claim(db, "evt_4", now=1) == "claimed", \
        "after a released claim the retry must not wait out the expiry"


# --------------------------------------------------- the shipped executable proof


def t_reference_pack_passes():
    r = subprocess.run(["node", "assert-money-invariants.mjs"], cwd=FIXTURES,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"the pack fails:\n{(r.stderr or r.stdout)[-600:]}"
    for inv in ("crash-after-receipt-is-retryable", "in-flight-claim-answers-retry-later",
                "completion-is-recorded-with-the-grant", "duplicate-of-completed-never-regrants"):
        assert f"pass {inv}" in r.stdout, f"the pack no longer asserts {inv}"


def t_reference_pack_self_test_passes():
    r = subprocess.run(["node", "assert-money-invariants.mjs", "--self-test"], cwd=FIXTURES,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"--self-test fails:\n{(r.stderr or r.stdout)[-600:]}"
    for rule in ("claim-completion", "claim-expiry"):
        assert rule in r.stdout, f"the self-test never exercised {rule}"


def main():
    case("the doctrine states the received/completed split", t_docs_state_the_split)
    case("crash after receipt admits a repeat worker", t_crash_after_receipt_admits_a_repeat_worker)
    case("duplicate of completed never regrants", t_duplicate_of_completed_never_regrants)
    case("the takeover race has exactly one winner", t_takeover_race_has_one_winner)
    case("release on throw readmits immediately", t_release_on_throw_readmits_immediately)
    case("the shipped pack proves all four invariants", t_reference_pack_passes)
    case("the pack's self-test still watches each rule fail", t_reference_pack_self_test_passes)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
