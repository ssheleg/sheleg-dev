#!/usr/bin/env python3
"""FIX-DV-05.01 — a credit follows a confirmed settlement, not a CAS success
(sherlock audit, DV-05).

The finding: creditUser ran after ANY successful updateMany(status notIn
final) — so a webhook that transitioned a payment to FAILED returned count=1
and credited the user; refunds and holds were swallowed by the
already-final "duplicate" return.

The fix under test, run as the documented state machine: the CAS advances
the lifecycle only; the grant is a second step gated on mapped === 'PAID'
and an immutable per-invoice ledger row (atomic dedup); refunds/holds take
their own path; a repeated paid delivery credits once.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SK = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "crypto-payments")
DOC = os.path.join(SK, "SKILL.md")
REF = os.path.join(SK, "references", "callback-route-hardening.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def t_doctrine_states_the_split():
    # The rule is in SKILL.md; the worked handler moved to the reference at the
    # house token ceiling (a split, not a trim). `//` stripped so a wrapped
    # comment line does not break a needle.
    sk = " ".join(open(DOC, encoding="utf-8").read().replace("//", " ").split())
    for needle in ("the payment's LIFECYCLE status, the immutable GRANT",
                   "it is not permission to credit",
                   "Credit only a confirmed settlement",
                   "refunds and holds take their own path and are never swallowed "
                   "as a duplicate",
                   "UNIQUE per-invoice grant-ledger row atomic with the credit"):
        assert needle in sk, f"SKILL.md no longer states {needle!r}"
    ref = " ".join(open(REF, encoding="utf-8").read().replace("//", " ").split())
    for needle in ("CREDIT ONLY A CONFIRMED SETTLEMENT",
                   "an immutable grant row keyed by invoice is the business dedup",
                   "a CAS that advanced a payment to FAILED returns `count: 1` too"):
        assert needle in ref, f"the reference no longer states {needle!r}"


# ------------- the documented handler, executed


FINAL = {"PAID", "FAILED", "REFUNDED", "EXPIRED"}


class System:
    def __init__(self):
        self.status = {}          # invoiceId -> lifecycle status
        self.granted = set()      # invoiceId with a grant ledger row (UNIQUE)
        self.credited = {}        # invoiceId -> times credited
        self.refunds = []

    def webhook(self, invoice, mapped):
        # 1. CAS the lifecycle (any non-final transition succeeds)
        cur = self.status.get(invoice)
        advanced = cur not in FINAL
        if advanced:
            self.status[invoice] = mapped
        # 2. refunds/holds: own path
        if mapped in ("REFUNDED", "ON_HOLD"):
            self.refunds.append((invoice, mapped))
            return "refund-or-hold"
        if not advanced:
            return "duplicate"
        # 3. credit ONLY a confirmed settlement, once (UNIQUE grant row)
        if mapped == "PAID":
            if invoice in self.granted:
                return "already-granted"
            self.granted.add(invoice)
            self.credited[invoice] = self.credited.get(invoice, 0) + 1
            return "credited"
        return "advanced-no-grant"


def t_failed_does_not_credit():
    s = System()
    r = s.webhook("inv-1", "FAILED")
    assert r == "advanced-no-grant", f"a FAILED webhook did {r}"
    assert s.credited == {}, "a failed payment credited the user — the finding itself"
    assert s.status["inv-1"] == "FAILED"


def t_underpaid_does_not_credit():
    s = System()
    assert s.webhook("inv-2", "UNDERPAID") == "advanced-no-grant"
    assert "inv-2" not in s.credited


def t_paid_credits_exactly_once():
    s = System()
    assert s.webhook("inv-3", "PAID") == "credited"
    assert s.webhook("inv-3", "PAID") == "duplicate"   # already final, CAS no-ops
    assert s.credited["inv-3"] == 1, "a repeated paid delivery double-credited"


def t_refund_is_not_swallowed_as_duplicate():
    s = System()
    s.webhook("inv-4", "PAID")
    r = s.webhook("inv-4", "REFUNDED")
    assert r == "refund-or-hold", \
        "a refund after paid was dropped as a duplicate — the finding's second half"
    assert ("inv-4", "REFUNDED") in s.refunds


def t_grant_survives_a_reordered_replay():
    # A late PAID replay for an invoice already granted must not credit again,
    # even if the lifecycle CAS were somehow re-openable.
    s = System()
    s.webhook("inv-5", "PAID")
    s.status["inv-5"] = "PROCESSING"          # simulate an errant re-open
    assert s.webhook("inv-5", "PAID") == "already-granted", \
        "the immutable grant row did not stop a second credit"
    assert s.credited["inv-5"] == 1


def main():
    case("the doctrine states the lifecycle/grant/refund split",
         t_doctrine_states_the_split)
    case("a FAILED webhook advances the lifecycle and grants nothing",
         t_failed_does_not_credit)
    case("an UNDERPAID webhook does not credit", t_underpaid_does_not_credit)
    case("a PAID webhook credits exactly once", t_paid_credits_exactly_once)
    case("a refund after paid is not swallowed as a duplicate",
         t_refund_is_not_swallowed_as_duplicate)
    case("the immutable grant row stops a reordered replay",
         t_grant_survives_a_reordered_replay)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
