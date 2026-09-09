#!/usr/bin/env python3
"""FIX-DV-03.01 — durable operation intent (sherlock audit, finding DV-03).

The finding: the seat-change example reverted the QUANTITY on a DB failure
with proration "none" — but `always_invoice` had already charged the
customer, so the compensation restored the count and kept the money. And an
ambiguous network outcome after the Stripe call had no state at all.

The fix under test, run as the documented state machine: the operation row
(with idempotency key) exists BEFORE the Stripe effect; a timeout after a
possibly-accepted effect is `unknown` and reachable by reconciliation, never
`failed`; a DB failure after Stripe confirmed leaves Stripe alone and repairs
the DB from the confirmed state; a business rollback is a second financial
operation (credit note) with its own tracked state.

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
    # `//` stripped: the rules under test live partly in code comments, and a
    # wrapped comment line would otherwise break a needle mid-sentence.
    flat = " ".join(open(DOC, encoding="utf-8").read().replace("//", " ").split())
    for needle in ("Durable intent, BEFORE the effect",
                   "idempotencyKey: op.idempotencyKey",
                   'data: { state: "unknown" }',
                   "unknown and leave it for reconciliation",
                   "the database is what gets repaired, from the confirmed Stripe state",
                   "returns none of it",
                   "SECOND financial operation, not a flag",
                   "stripe.creditNotes.create"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    assert "// compensating revert" not in flat, \
        "the quantity-revert-as-compensation example survived"


# ------------- the documented state machine, executed


class Stripe:
    """Remote side: accepts, declines, or times out AFTER accepting."""

    def __init__(self, mode="ok"):
        self.mode = mode
        self.quantity = 1
        self.invoiced = 0
        self.credit_notes = []
        self.seen_keys = {}

    def update(self, qty, idempotency_key):
        if idempotency_key in self.seen_keys:
            return self.seen_keys[idempotency_key]      # replay, no double charge
        if self.mode == "card-declined":
            raise ValueError("StripeCardError")
        self.quantity = qty
        self.invoiced += 10 * (qty - 1)                  # the proration charge
        self.seen_keys[idempotency_key] = {"quantity": qty}
        if self.mode == "timeout-after-accept":
            raise TimeoutError("StripeConnectionError")
        return {"quantity": qty}

    def credit_note(self, amount):
        self.credit_notes.append(amount)


class Handler:
    def __init__(self, stripe, db_fails=False):
        self.stripe = stripe
        self.db_fails = db_fails
        self.ops = []
        self.db_quantity = 1

    def change_quantity(self, new_qty):
        op = {"id": len(self.ops), "kind": "quantity-change", "to": new_qty,
              "state": "pending", "key": str(uuid.uuid4())}
        self.ops.append(op)                              # BEFORE the effect
        try:
            self.stripe.update(new_qty, op["key"])
        except ValueError:
            op["state"] = "failed"
            return 402
        except TimeoutError:
            op["state"] = "unknown"                      # never failed
            return 202
        if self.db_fails:
            op["state"] = "apply-pending"                # Stripe untouched
            return 500
        self.db_quantity = new_qty
        op["state"] = "applied"
        return 200

    def reconcile(self):
        for op in self.ops:
            if op["state"] in ("unknown", "apply-pending"):
                remote = self.stripe.seen_keys.get(op["key"])
                if remote:                               # effect was accepted
                    self.db_quantity = remote["quantity"]
                    op["state"] = "applied"
                else:
                    op["state"] = "failed"

    def business_rollback(self, op_id, old_qty):
        comp = {"id": len(self.ops), "kind": "credit-note",
                "state": "pending", "key": str(uuid.uuid4())}
        self.ops.append(comp)
        self.stripe.update(old_qty, comp["key"] + ":qty")
        self.stripe.credit_note(self.stripe.invoiced)
        comp["state"] = "applied"
        return comp


def t_intent_exists_before_the_effect():
    s = Stripe("card-declined")
    h = Handler(s)
    assert h.change_quantity(3) == 402
    assert h.ops and h.ops[0]["state"] == "failed" and h.ops[0]["key"], \
        "no durable op row with a key survived the declined path"


def t_timeout_is_unknown_and_reconcilable():
    s = Stripe("timeout-after-accept")
    h = Handler(s)
    assert h.change_quantity(3) == 202
    assert h.ops[0]["state"] == "unknown", \
        f"an ambiguous outcome was {h.ops[0]['state']!r} — the finding itself"
    h.reconcile()
    assert h.ops[0]["state"] == "applied" and h.db_quantity == 3, \
        "reconciliation did not settle the unknown op from the accepted effect"
    assert s.invoiced == 20, "the charge was double-counted or lost"


def t_db_failure_repairs_db_not_stripe():
    s = Stripe()
    h = Handler(s, db_fails=True)
    assert h.change_quantity(3) == 500
    assert s.quantity == 3, \
        "Stripe was reverted to match a broken local write — the money stayed taken"
    h.db_fails = False
    h.reconcile()
    assert h.db_quantity == 3 and h.ops[0]["state"] == "applied", \
        "the DB was not repaired from the confirmed Stripe state"


def t_rollback_returns_the_money_with_its_own_state():
    s = Stripe()
    h = Handler(s)
    h.change_quantity(3)
    charged = s.invoiced
    comp = h.business_rollback(0, old_qty=1)
    assert s.quantity == 1
    assert s.credit_notes == [charged], \
        "the rollback restored the count and kept the charge — the finding itself"
    assert comp["state"] == "applied" and comp["kind"] == "credit-note", \
        "the compensation has no tracked state of its own"


def t_replayed_key_does_not_double_charge():
    s = Stripe()
    h = Handler(s)
    h.change_quantity(3)
    key = h.ops[0]["key"]
    s.update(3, key)                                     # reconciler replays
    assert s.invoiced == 20, "a replayed idempotency key charged twice"


def main():
    case("the doctrine states the rules; the quantity-revert example is gone",
         t_doctrine_states_the_rules)
    case("the op row exists before the effect", t_intent_exists_before_the_effect)
    case("a timeout after an accepted effect is unknown, then reconciled",
         t_timeout_is_unknown_and_reconcilable)
    case("a DB failure repairs the DB from Stripe, never the reverse",
         t_db_failure_repairs_db_not_stripe)
    case("a business rollback returns the money with its own tracked state",
         t_rollback_returns_the_money_with_its_own_state)
    case("a replayed idempotency key does not double charge",
         t_replayed_key_does_not_double_charge)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
