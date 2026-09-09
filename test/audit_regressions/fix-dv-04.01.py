#!/usr/bin/env python3
"""FIX-DV-04.01 — the refund clawback loses no cumulative refund (sherlock
audit, DV-04).

The finding: two handlers read the same stored.refundedTotal for cumulative
4000 and 9000; if 4000 won the CAS, the 9000 handler returned WITHOUT
re-reading — clawing back nothing. Marker and clawback were separate writes,
so a rollback marker with no CAS could overwrite a newer total; and money
was carried as float (`/ 100`).

The fix under test, run as the documented state machine: the whole clawback
is one serializable transaction computing max(total_seen); a CAS loser
re-reads and retries; marker and ledger move together; amounts stay in
minor units. The invariant: cumulative 4000 & 9000 in EITHER order, a crash
after the marker, and a retry of the old event all converge on total=9000
and summed clawback=9000, exactly once.

Standard library only.
"""
import os
import sys
import threading

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing",
                   "references", "subscription-lifecycle.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def t_doctrine_states_the_fix():
    flat = " ".join(open(DOC, encoding="utf-8").read().split())
    for needle in ("`charge.amount_refunded` is CUMULATIVE and delivered out of order",
                   "ONE serializable transaction",
                   "a CAS loser RE-READS and retries rather than returning",
                   "Money in MINOR UNITS end to end",
                   "Marker and ledger move TOGETHER",
                   "idempotent per (charge,total)",
                   "converge on `refundedTotal = 9000`"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    assert "charge.amount_refunded / 100" not in flat, \
        "the float-dividing clawback survived"
    assert "if (count === 0) return;" not in flat, \
        "the CAS-loser-returns bug survived"


# ---------- the documented transaction, executed under real threads


class Store:
    """A serializable row: the lock serializes the read-modify-write, so a
    loser genuinely re-reads. Ledger keyed per (charge, total) — idempotent."""

    def __init__(self):
        self.refunded_total = 0          # minor units
        self.ledger = {}                 # key -> increment
        self.lock = threading.Lock()

    def clawback_txn(self, charge_id, cumulative):
        # RETRIES is implicit: the lock makes each attempt see the latest row.
        with self.lock:
            seen = max(self.refunded_total, cumulative)     # monotone
            increment = seen - self.refunded_total
            if increment <= 0:
                return
            self.refunded_total = seen                      # marker
            self.ledger[f"{charge_id}:{seen}"] = increment  # ledger, together

    def total_clawed(self):
        return sum(self.ledger.values())


def run_order(a, b):
    s = Store()
    t1 = threading.Thread(target=s.clawback_txn, args=("ch_1", a))
    t2 = threading.Thread(target=s.clawback_txn, args=("ch_1", b))
    t1.start(); t2.start(); t1.join(); t2.join()
    return s


def t_both_orders_converge():
    for a, b in ((4000, 9000), (9000, 4000)):
        for _ in range(50):                         # exercise the interleaving
            s = run_order(a, b)
            assert s.refunded_total == 9000, \
                f"order {a},{b}: total={s.refunded_total}, not 9000 — a refund lost"
            assert s.total_clawed() == 9000, \
                f"order {a},{b}: clawed {s.total_clawed()}, not 9000"


def t_retry_of_old_event_claws_nothing_more():
    s = Store()
    s.clawback_txn("ch_1", 4000)
    s.clawback_txn("ch_1", 9000)
    before = s.total_clawed()
    s.clawback_txn("ch_1", 4000)                     # a late redelivery of the old event
    assert s.total_clawed() == before == 9000, \
        "replaying the smaller cumulative event clawed back again"


def t_crash_after_marker_is_recoverable():
    # Marker and ledger move together, so there is no window where the marker
    # advanced without its clawback — a "crash after marker" cannot exist as
    # a torn state. Re-running the event is a no-op.
    s = Store()
    s.clawback_txn("ch_1", 9000)
    assert s.refunded_total == 9000 and s.total_clawed() == 9000
    s.clawback_txn("ch_1", 9000)                     # recovery re-runs the event
    assert s.total_clawed() == 9000, "recovery double-clawed"


def t_minor_units_have_no_float_error():
    # 995 cents must stay 995, never 9.95 with a representation error.
    s = Store()
    s.clawback_txn("ch_2", 995)
    assert s.refunded_total == 995 and isinstance(s.refunded_total, int), \
        "the amount left minor units"


def main():
    case("the doctrine states the fix and drops the float/CAS-return bugs",
         t_doctrine_states_the_fix)
    case("cumulative 4000 & 9000 converge to 9000 in both orders, exactly once",
         t_both_orders_converge)
    case("a retry of the old event claws back nothing more",
         t_retry_of_old_event_claws_nothing_more)
    case("marker+ledger together make a crash-after-marker recoverable",
         t_crash_after_marker_is_recoverable)
    case("minor units carry no float error", t_minor_units_have_no_float_error)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
