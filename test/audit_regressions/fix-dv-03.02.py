#!/usr/bin/env python3
"""FIX-DV-03.02 — reconcile-first compensation (sherlock audit, second leaf
of DV-03, on FIX-DV-03.01's durable operation intent).

The rules under test, run as the documented reconciler: the default repairs
the DATABASE from the confirmed Stripe state (a record repair, never called
a refund — no money moved); a refund happens only under an explicitly
configured business policy; and reconciliation is idempotent — settled rows
are absorbing, a replay changes nothing and never issues a second credit
note.

Standard library only.
"""
import os
import sys
import uuid

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


def t_doctrine_states_the_rules():
    flat = " ".join(open(DOC, encoding="utf-8").read().replace("//", " ").split())
    for needle in ("Reconciliation — repair the record, and money moves only by policy",
                   "updating the local count is never called a refund",
                   "Idempotent by construction",
                   "A reconciler that can move money on a replay is a billing bug "
                   "wearing a repair's name",
                   "A refund is a POLICY, never a reflex",
                   "AT MOST ONCE per operation",
                   "op.idempotencyKey}:credit"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"


# ------------- the documented reconciler, executed


class Stripe:
    def __init__(self):
        self.quantity = 3
        self.credit_notes = {}

    def retrieve(self):
        return self.quantity

    def credit_note(self, key, amount):
        if key in self.credit_notes:
            return self.credit_notes[key]
        self.credit_notes[key] = {"id": f"cn_{len(self.credit_notes)}", "amount": amount}
        return self.credit_notes[key]


class System:
    def __init__(self, stripe, policy="repair-only"):
        self.stripe = stripe
        self.policy = policy
        self.db_quantity = 1
        self.ops = [{"id": 1, "kind": "quantity-change", "to": 3,
                     "state": "unknown", "key": str(uuid.uuid4()),
                     "charged": 20, "credit_note_id": None}]
        self.events = []

    def reconcile(self):
        for op in self.ops:
            if op["state"] in ("unknown", "apply-pending"):
                if self.stripe.retrieve() == op["to"]:
                    self.db_quantity = op["to"]
                    op["state"] = "applied"
                    self.events.append("record-repair")     # not a refund
                else:
                    op["state"] = "failed"
            if self.policy == "revert-and-credit" and op["state"] == "applied" \
                    and op["credit_note_id"] is None:
                note = self.stripe.credit_note(op["key"] + ":credit", op["charged"])
                op["credit_note_id"] = note["id"]
                op["state"] = "compensated"
                self.events.append("refund")


def t_default_repairs_record_and_is_not_a_refund():
    s = System(Stripe())
    s.reconcile()
    assert s.db_quantity == 3 and s.ops[0]["state"] == "applied"
    assert s.events == ["record-repair"] and "refund" not in s.events, \
        "a local count repair was called (or performed as) a refund"
    assert s.stripe.credit_notes == {}, "money moved without a policy"


def t_repeated_reconciliation_moves_no_money():
    s = System(Stripe(), policy="revert-and-credit")
    s.reconcile()
    assert s.ops[0]["state"] == "compensated"
    notes_after_first = dict(s.stripe.credit_notes)
    for _ in range(5):
        s.reconcile()
    assert s.stripe.credit_notes == notes_after_first and \
        len(s.stripe.credit_notes) == 1, \
        "a repeated reconciliation issued a second credit note — the finding itself"
    assert s.events.count("refund") == 1


def t_refund_only_under_explicit_policy():
    s = System(Stripe(), policy="repair-only")
    s.reconcile()
    s.reconcile()
    assert s.stripe.credit_notes == {} and s.ops[0]["state"] == "applied", \
        "a refund fired without the business policy asking for it"


def t_settled_rows_are_absorbing():
    s = System(Stripe())
    s.reconcile()
    s.stripe.quantity = 99                      # the world changes later
    s.reconcile()
    assert s.db_quantity == 3 and s.ops[0]["state"] == "applied", \
        "a settled row was re-opened by a later reconciliation"


def main():
    case("the doctrine states the rules", t_doctrine_states_the_rules)
    case("the default repairs the record and is not a refund",
         t_default_repairs_record_and_is_not_a_refund)
    case("repeated reconciliation moves no money", t_repeated_reconciliation_moves_no_money)
    case("a refund happens only under the explicit policy",
         t_refund_only_under_explicit_policy)
    case("settled rows are absorbing", t_settled_rows_are_absorbing)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
