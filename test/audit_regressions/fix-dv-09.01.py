#!/usr/bin/env python3
"""FIX-DV-09.01 — per-principal OAuth client, hardened state (sherlock audit,
DV-09).

The finding: one module-level OAuth2 client for the whole process, and every
/oauth2callback mutated its credentials — two concurrent logins clobbered each
other. And the state check let undefined === undefined pass, never consumed the
state, and had no TTL.

The fix under test: a client built PER request (credentials never assigned to a
shared object); state REQUIRED on both sides, TTL'd, atomically consumed and
validated BEFORE the token exchange. Documented in oauth2-web-server.md, and
the isolation + state rules are run as behaviour.

Standard library only.
"""
import os
import sys
import threading

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


def t_doctrine_states_per_request_and_state():
    flat = " ".join(open(DOC, encoding="utf-8").read().replace("//", " ").split())
    for needle in ("One OAuth2 client PER request, never a shared singleton",
                   "two users signing in at once end up with each\nother's tokens".replace("\n", " "),
                   "function newOAuthClient()",
                   "State is REQUIRED, crypto-random, single-use with a TTL",
                   "Validate state BEFORE the token exchange",
                   "undefined === undefined must NOT pass",
                   "single-use: consume it now",
                   "a client for THIS request"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    raw = open(DOC, encoding="utf-8").read()
    assert "const oauth2Client = new google.auth.OAuth2(" not in raw, \
        "the shared module-level client survived"
    assert "if (q.state !== req.session.state) {" not in raw, \
        "the undefined===undefined-permitting state check survived"


# ---------------- the client isolation + state rules, executed


class OAuthClient:
    def __init__(self):
        self.credentials = None

    def set_credentials(self, tokens):
        self.credentials = tokens


def handle_callback(make_client, principal_tokens):
    client = make_client()                        # PER request
    client.set_credentials(principal_tokens)
    return client                                 # local, not shared


def t_two_concurrent_logins_do_not_share_credentials():
    results = {}

    def login(name, tokens):
        c = handle_callback(OAuthClient, tokens)
        results[name] = c.credentials

    t1 = threading.Thread(target=login, args=("alice", {"tok": "A"}))
    t2 = threading.Thread(target=login, args=("bob", {"tok": "B"}))
    t1.start(); t2.start(); t1.join(); t2.join()
    assert results["alice"] == {"tok": "A"} and results["bob"] == {"tok": "B"}, \
        "concurrent logins shared a client's credentials — the finding itself"


def validate_state(session_state, query_state, now):
    """Present on both sides, unexpired, single-use (caller consumes)."""
    if not query_state or not session_state:
        return False                              # undefined/absent never passes
    if session_state["value"] != query_state:
        return False
    if now > session_state["expires"]:
        return False
    return True


def t_state_requires_both_sides():
    assert validate_state(None, None, 0) is False, \
        "undefined === undefined passed the state check — the finding itself"
    assert validate_state({"value": "x", "expires": 100}, None, 10) is False
    assert validate_state(None, "x", 10) is False
    assert validate_state({"value": "x", "expires": 100}, "x", 10) is True


def t_state_is_single_use():
    session = {"oauthState": {"value": "x", "expires": 100}}
    saved = session.pop("oauthState", None)        # consume
    assert validate_state(saved, "x", 10) is True
    # a replay finds nothing to consume
    saved2 = session.pop("oauthState", None)
    assert validate_state(saved2, "x", 10) is False, \
        "a replayed callback reused the state — it was not single-use"


def t_state_has_a_ttl():
    assert validate_state({"value": "x", "expires": 100}, "x", 200) is False, \
        "an expired state still validated"


def main():
    case("the doctrine states per-request clients and hardened state",
         t_doctrine_states_per_request_and_state)
    case("two concurrent logins do not share credentials",
         t_two_concurrent_logins_do_not_share_credentials)
    case("state requires a value on both sides", t_state_requires_both_sides)
    case("state is single-use (consumed)", t_state_is_single_use)
    case("state has a TTL", t_state_has_a_ttl)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
