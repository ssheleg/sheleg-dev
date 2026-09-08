#!/usr/bin/env python3
"""FIX-DV-01.02 — atomic business application (sherlock audit, finding DV-01,
second leaf; depends on FIX-DV-01.01's received/completed split).

The contract under test: entitlement, business dedup marker, completion mark
and the outbox rows commit in ONE transaction; the side-effect consumer holds
its OWN dedup key because the outbox delivers at least once.

Acceptance: a crash before the commit applies nothing; after the commit a
retry duplicates neither the grant nor the send.

Proved twice: the documented SQL semantics executed in sqlite (a real
transaction, really rolled back), and the shipped reference pack re-run as a
process with its three new invariants and their mutants.

Standard library only.
"""
import os
import sqlite3
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIXTURES = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing", "fixtures")
EVENTS = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing",
                      "references", "webhook-events.md")
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing", "SKILL.md")

checks = 0
failures = []


def case(name, fn):
    global checks
    try:
        fn()
        checks += 1
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


# ------------------------------------------------------------------ the doctrine


def t_doctrine_states_the_transaction_and_the_key():
    flat = " ".join(open(EVENTS, encoding="utf-8").read().split())
    for needle in ("## One transaction, then the outbox",
                   "commit together, or none of them exist",
                   "the retry runs the whole application again",
                   "A redelivered outbox row must send nothing twice",
                   "own dedup key"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    skill = open(SKILL, encoding="utf-8").read()
    assert "outbox rows" in skill and "own consumer key" in skill, \
        "SKILL.md handler-order bullet lost the transaction/outbox wording"


# ---------------------------- the documented semantics, executed in sqlite


class Crash(Exception):
    pass


def store():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE grants (event_id TEXT PRIMARY KEY)")
    db.execute("CREATE TABLE markers (period TEXT PRIMARY KEY)")
    db.execute("""CREATE TABLE events (
        id TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'processing')""")
    db.execute("""CREATE TABLE outbox (
        key TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'pending')""")
    db.execute("CREATE TABLE sent (key TEXT PRIMARY KEY)")  # the CONSUMER's own dedup
    return db


def apply_event(db, eid, period, crash_before_commit=False):
    """The documented shape: one transaction for everything, or nothing."""
    db.execute("INSERT OR IGNORE INTO events (id) VALUES (?)", (eid,))
    db.commit()  # the RECEIPT is durable before the work — FIX-DV-01.01's contract
    row = db.execute("SELECT state FROM events WHERE id = ?", (eid,)).fetchone()
    if row[0] == "completed":
        return "duplicate"
    try:
        with db:  # one transaction
            if db.execute("SELECT 1 FROM markers WHERE period = ?", (period,)).fetchone():
                db.execute("UPDATE events SET state = 'completed' WHERE id = ?", (eid,))
                return "already-granted"
            db.execute("INSERT INTO grants VALUES (?)", (eid,))
            db.execute("INSERT INTO markers VALUES (?)", (period,))
            db.execute("UPDATE events SET state = 'completed' WHERE id = ?", (eid,))
            for kind in ("renewal-notice", "conversion"):
                db.execute("INSERT INTO outbox (key) VALUES (?)", (f"{eid}:{kind}",))
            if crash_before_commit:
                raise Crash()
    except Crash:
        return "crashed"
    drain(db)
    return "applied"


def drain(db):
    """The consumer: at-least-once rows, its own key in `sent`."""
    for (key,) in db.execute("SELECT key FROM outbox WHERE state = 'pending'").fetchall():
        if not db.execute("SELECT 1 FROM sent WHERE key = ?", (key,)).fetchone():
            db.execute("INSERT INTO sent VALUES (?)", (key,))
        db.execute("UPDATE outbox SET state = 'sent' WHERE key = ?", (key,))


def counts(db):
    g = db.execute("SELECT count(*) FROM grants").fetchone()[0]
    s = db.execute("SELECT count(*) FROM sent").fetchone()[0]
    return g, s


def t_crash_before_commit_applies_nothing():
    db = store()
    assert apply_event(db, "evt_1", "2026-09", crash_before_commit=True) == "crashed"
    assert counts(db) == (0, 0), f"a rolled-back transaction left state behind: {counts(db)}"
    assert db.execute("SELECT count(*) FROM outbox").fetchone()[0] == 0, \
        "an outbox row survived the rollback"
    state, = db.execute("SELECT state FROM events WHERE id = 'evt_1'").fetchone()
    assert state == "processing", f"the claim row left 'processing': {state!r}"
    # the retry applies everything exactly once
    assert apply_event(db, "evt_1", "2026-09") == "applied"
    assert counts(db) == (1, 2), f"the retry did not apply exactly once: {counts(db)}"


def t_committed_retry_duplicates_nothing():
    db = store()
    assert apply_event(db, "evt_2", "2026-10") == "applied"
    assert apply_event(db, "evt_2", "2026-10") == "duplicate", "a completed event reprocessed"
    # the queue redelivers every outbox row
    db.execute("UPDATE outbox SET state = 'pending'")
    drain(db)
    assert counts(db) == (1, 2), f"a redelivered outbox row sent again: {counts(db)}"


def t_consumer_key_is_the_only_guard():
    """The negative: without the consumer key, redelivery double-sends — the
    defect the key exists for, watched failing."""
    db = store()
    apply_event(db, "evt_3", "2026-11")
    db.execute("UPDATE outbox SET state = 'pending'")
    sends = 0
    for (key,) in db.execute("SELECT key FROM outbox WHERE state = 'pending'").fetchall():
        sends += 1  # no `sent` lookup: the mutant
        db.execute("UPDATE outbox SET state = 'sent' WHERE key = ?", (key,))
    assert sends == 2, "the mutant did not reproduce the double send"


# ------------------------------------------------- the shipped executable proof


def t_reference_pack_proves_it():
    r = subprocess.run(["node", "assert-money-invariants.mjs"], cwd=FIXTURES,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"the pack fails:\n{(r.stderr or r.stdout)[-500:]}"
    for inv in ("transaction-rolls-back-whole", "crash-before-commit-applies-nothing",
                "committed-retry-sends-once"):
        assert f"pass {inv}" in r.stdout, f"the pack no longer asserts {inv}"
    st = subprocess.run(["node", "assert-money-invariants.mjs", "--self-test"], cwd=FIXTURES,
                        capture_output=True, text=True, timeout=600)
    assert st.returncode == 0, f"--self-test fails:\n{(st.stderr or st.stdout)[-500:]}"
    for rule in ("atomic-application", "outbox-consumer-key"):
        assert rule in st.stdout, f"the self-test never exercised {rule}"


def main():
    case("the doctrine states one transaction and the consumer key",
         t_doctrine_states_the_transaction_and_the_key)
    case("crash before commit applies nothing; the retry applies once",
         t_crash_before_commit_applies_nothing)
    case("after the commit, retry duplicates neither grant nor send",
         t_committed_retry_duplicates_nothing)
    case("without the consumer key the double send comes back", t_consumer_key_is_the_only_guard)
    case("the shipped pack proves all three invariants with their mutants",
         t_reference_pack_proves_it)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print(f"OK ({checks} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
