#!/usr/bin/env python3
"""FIX-DV-02.01 — unique subscription grant (sherlock audit, finding DV-02).

The finding: the renewal example guarded replays with a high-water mark
(`lastGrantedPeriodStart >= periodStart`) — which contradicts the
reordered-periods fixture (a late-arriving OLDER period would be suppressed) —
and its SELECT-then-write did not serialize the grant, so two concurrent
grants of one period both passed the read.

The fix under test: one ledger row per granted period, arbitrated by a UNIQUE
key the database enforces; the row carries subscription, item, invoice and
period (invoice as provenance, never uniqueness); the grant is atomic with the
key write; a new — even older-dated — period is never suppressed.

Proved via the documented SQL in sqlite AND the shipped pack as a process.
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
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing",
                   "references", "subscription-lifecycle.md")

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


def t_doctrine_replaced_the_high_water_mark():
    flat = " ".join(open(DOC, encoding="utf-8").read().split())
    for needle in ("UNIQUE (subscriptionId, periodStart)",
                   "never a high-water mark",
                   "would read as a replay and be suppressed",
                   "both pass the read and both credit",
                   "concurrent-entry-points-grant-once"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    assert "lastGrantedPeriodStart && sub.lastGrantedPeriodStart >=" not in flat, \
        "the high-water guard survived in the example"


def store():
    db = sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE grant_ledger (
        subscription TEXT NOT NULL, item TEXT NOT NULL, invoice TEXT NOT NULL,
        period INTEGER NOT NULL, UNIQUE (subscription, period))""")
    return db


def grant(db, sub, item, invoice, period):
    """The documented shape: the INSERT is the claim; a unique violation is the replay."""
    try:
        with db:
            db.execute("INSERT INTO grant_ledger VALUES (?,?,?,?)",
                       (sub, item, invoice, period))
        return True
    except sqlite3.IntegrityError:
        return False


def grants(db):
    return db.execute("SELECT period, invoice FROM grant_ledger ORDER BY period").fetchall()


def t_concurrent_same_period_grants_once():
    db = store()
    results = [grant(db, "sub_1", "it_1", "in_jan", 100),
               grant(db, "sub_1", "it_1", "in_jan_retry", 100)]  # second invoice, same period
    assert results == [True, False], f"one period was granted twice: {results}"
    assert len(grants(db)) == 1


def t_older_period_is_never_suppressed():
    db = store()
    assert grant(db, "sub_1", "it_1", "in_feb", 200)   # February lands first
    assert grant(db, "sub_1", "it_1", "in_jan", 100), \
        "a late-arriving OLDER period was suppressed — the high-water defect"
    assert [p for p, _ in grants(db)] == [100, 200]


def t_invoice_is_provenance_not_uniqueness():
    db = store()
    grant(db, "sub_1", "it_1", "in_a", 300)
    assert not grant(db, "sub_1", "it_1", "in_b", 300), \
        "a second invoice for one period granted it twice"
    assert grants(db) == [(300, "in_a")], "the ledger lost the provenance of the winner"


def t_pack_proves_the_race():
    r = subprocess.run(["node", "assert-money-invariants.mjs"], cwd=FIXTURES,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"the pack fails:\n{(r.stderr or r.stdout)[-400:]}"
    assert "pass concurrent-entry-points-grant-once" in r.stdout, \
        "the pack no longer asserts the entry-point race"
    assert "pass out-of-order-pair-does-not-rewind-state" in r.stdout, \
        "the reordered-periods invariant is gone"
    st = subprocess.run(["node", "assert-money-invariants.mjs", "--self-test"], cwd=FIXTURES,
                        capture_output=True, text=True, timeout=600)
    assert st.returncode == 0 and "grant-key-atomic" in st.stdout, \
        f"--self-test does not exercise grant-key-atomic:\n{(st.stderr or st.stdout)[-300:]}"


def main():
    case("the doctrine replaced the high-water mark", t_doctrine_replaced_the_high_water_mark)
    case("concurrent grants of one period land once", t_concurrent_same_period_grants_once)
    case("an older period is never suppressed", t_older_period_is_never_suppressed)
    case("the invoice is provenance, never uniqueness", t_invoice_is_provenance_not_uniqueness)
    case("the shipped pack proves the race and the reorder", t_pack_proves_the_race)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print(f"OK ({checks} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
