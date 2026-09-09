#!/usr/bin/env python3
"""FIX-DV-09.02 — one-time OAuth state: server-bound, TTL'd, consumed
atomically BEFORE the exchange (sherlock audit, DV-09).

The finding: every Python example validated state as
`request.args.get('state') != session.get('state')` — None == None PASSES, so
a callback with no state at all against a fresh session started a token
exchange; the state had no TTL; and it was never consumed, so the same
callback URL could be replayed for as long as the session lived.

The fix under test:
* every Python block stores `{'value', 'expires'}` server-side and the
  callback POPs it (atomic consume) and validates presence-on-both-sides,
  match and TTL BEFORE any fetch_token;
* no `session['state'] = state` / `session.get('state')` comparison survives;
* the consume-then-validate rule is RUN as behaviour: wrong, missing, expired
  and replayed states never reach the exchange.

Standard library only.
"""
import os
import re
import sys
import time

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-auth",
                   "references", "oauth2-web-server.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def doc():
    with open(DOC, encoding="utf-8") as fh:
        return fh.read()


def t_no_naked_state_comparison_survives():
    d = doc()
    assert "session['state'] = state" not in d, \
        "a TTL-less server state assignment survived"
    assert ".get('state') != session.get('state')" not in d and \
           ".get('state') != request.session.get('state')" not in d, \
        "the None == None comparison survived — a stateless callback would pass"


def t_every_python_callback_pops_before_exchange():
    d = doc()
    # every fetch_token in the doc must be preceded (in its block) by a pop
    blocks = re.findall(r"```python(.*?)```", d, re.S)
    exchanging = [b for b in blocks if "fetch_token" in b]
    assert exchanging, "no python exchange blocks found — the doc moved"
    for b in exchanging:
        if "authorization_url" in b and "fetch_token" not in b.split("fetch_token")[0]:
            pass
        pop_at = b.find(".pop('oauth_state'")
        ex_at = b.find("fetch_token")
        assert pop_at != -1, "an exchange block never consumes the state"
        assert pop_at < ex_at, "the state is consumed AFTER the exchange"
        assert "expires" in b[pop_at:ex_at], "the TTL is not checked before the exchange"
        assert "not got or not saved" in b[pop_at:ex_at], \
            "presence-on-both-sides is not required before the exchange"


def t_setters_carry_ttl():
    d = doc()
    setters = d.count("'oauth_state'] = {'value': state, 'expires': time.time() + 600}")
    assert setters >= 3, f"only {setters} TTL'd setters — a python block still stores a bare string"


# ---------------- the rule, run as behaviour


class Session(dict):
    pass


def callback(session, query, now):
    """The doc's consume-then-validate rule, verbatim in shape."""
    saved = session.pop("oauth_state", None)          # atomic consume
    got = query.get("state")
    if (not got or not saved or saved["value"] != got
            or now > saved["expires"]):
        return "403"
    return "exchange"                                  # only now may fetch_token run


def t_wrong_missing_expired_replayed_never_exchange():
    now = time.time()
    fresh = lambda: Session(oauth_state={"value": "s1", "expires": now + 600})
    assert callback(fresh(), {"state": "s1"}, now) == "exchange"
    assert callback(fresh(), {"state": "WRONG"}, now) == "403"
    assert callback(fresh(), {}, now) == "403", "a missing state started an exchange"
    assert callback(Session(), {}, now) == "403", "None == None passed — the finding itself"
    assert callback(fresh(), {"state": "s1"}, now + 601) == "403", "an expired state passed"
    s = fresh()
    assert callback(s, {"state": "s1"}, now) == "exchange"
    assert callback(s, {"state": "s1"}, now) == "403", \
        "a replayed callback reused the state — consume was not atomic"


def main():
    case("no naked state comparison survives", t_no_naked_state_comparison_survives)
    case("every python callback consumes state (with TTL) before the exchange",
         t_every_python_callback_pops_before_exchange)
    case("every python setter stores value+expires", t_setters_carry_ttl)
    case("wrong/missing/expired/replayed state never starts an exchange",
         t_wrong_missing_expired_replayed_never_exchange)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
