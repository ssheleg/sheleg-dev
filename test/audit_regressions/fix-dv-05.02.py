#!/usr/bin/env python3
"""FIX-DV-05.02 — refund and hold lifecycle: a separate ledger, not a
duplicate (sherlock audit, DV-05 leaf 2, on FIX-DV-05.01).

The finding: refund/hold events arriving after `paid` were dropped by the
already-final "duplicate" return. They belong to a separate ledger, keyed by
(paymentId, status), idempotent: a paid→refund adjusts the balance once, a
repeated refund adds nothing.

The heleket §13 doctrine is checked, and the refund-ledger rules are run as
behaviour.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "crypto-payments",
                   "references", "heleket-provider.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def t_doctrine_states_the_separate_ledger():
    flat = " ".join(open(DOC, encoding="utf-8").read().split())
    for needle in ("refunds and holds are a SEPARATE ledger",
                   "never dropped as a \"duplicate\" just because the invoice\nalready "
                   "reached `paid`".replace("\n", " "),
                   "A refund event arriving after `paid` is the\nNORMAL case".replace("\n", " "),
                   "keyed by `(paymentId, status)`",
                   "debits ONCE, never twice"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    assert "**Optionally** debit the user's balance manually" not in flat, \
        "the vague optional-debit line survived"


# ---------------- the refund ledger, executed


class System:
    FINAL = {"paid", "failed", "refunded", "expired"}

    def __init__(self):
        self.status = {}
        self.balance = {}
        self.refund_ledger = set()     # (paymentId, status)
        self.credited = {}

    def paid(self, invoice, user, amount):
        if self.status.get(invoice) in self.FINAL:
            return "duplicate"
        self.status[invoice] = "paid"
        self.balance[user] = self.balance.get(user, 0) + amount
        self.credited[invoice] = (user, amount)
        return "credited"

    def refund(self, invoice, status):
        key = (invoice, status)
        if key in self.refund_ledger:
            return "duplicate-refund"       # idempotent, adds nothing
        self.refund_ledger.add(key)
        if status == "refund_paid" and invoice in self.credited:
            user, amount = self.credited[invoice]
            self.balance[user] = self.balance.get(user, 0) - amount
            return "debited"
        return "recorded"


def t_paid_then_refund_adjusts_once():
    s = System()
    assert s.paid("inv-1", "u", 100) == "credited"
    assert s.balance["u"] == 100
    r = s.refund("inv-1", "refund_paid")
    assert r == "debited", f"a refund after paid was not processed: {r}"
    assert s.balance["u"] == 0, "the credited amount was not reversed"


def t_repeated_refund_does_not_duplicate():
    s = System()
    s.paid("inv-2", "u", 50)
    s.refund("inv-2", "refund_paid")
    r = s.refund("inv-2", "refund_paid")          # redelivery
    assert r == "duplicate-refund", f"a repeated refund was processed again: {r}"
    assert s.balance["u"] == 0, "a redelivered refund debited twice"


def t_refund_not_swallowed_after_paid():
    s = System()
    s.paid("inv-3", "u", 30)
    # the paid path would call this a duplicate; the refund path must not
    assert s.status["inv-3"] == "paid"
    assert s.refund("inv-3", "refund_process") == "recorded", \
        "a refund_process after paid was dropped as a duplicate — the finding itself"


def t_hold_records_without_debit():
    s = System()
    s.paid("inv-4", "u", 20)
    assert s.refund("inv-4", "on_hold") == "recorded"
    assert s.balance["u"] == 20, "a hold debited the balance — it should only pause"


def main():
    case("the doctrine states the separate refund/hold ledger",
         t_doctrine_states_the_separate_ledger)
    case("paid then refund adjusts the balance exactly once",
         t_paid_then_refund_adjusts_once)
    case("a repeated refund does not duplicate", t_repeated_refund_does_not_duplicate)
    case("a refund after paid is not swallowed as a duplicate",
         t_refund_not_swallowed_after_paid)
    case("a hold records without debiting", t_hold_records_without_debit)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
