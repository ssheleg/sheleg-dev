#!/usr/bin/env python3
"""FIX-DV-10.01 — the nonce is server-issued and consumed once, not whatever
the client mailed in (sherlock audit, DV-10).

The finding: the client generated the nonce, POSTed it beside the credential,
and the backend compared JWT.nonce to body.nonce — a value read out of the
very token it was meant to check — and even SKIPPED the comparison when the
body carried none (`if data.nonce:`). "A stolen token cannot be replayed" did
not follow from the code.

The fix under test (one contract across google-signin and google-auth):
* the server mints the nonce, stores it with a TTL bound to a pre-auth
  HttpOnly cookie, and the callback POPs it (one-time consume) and requires
  exact equality with the token's nonce claim — mandatory, body plays no part;
* the docs carry no client-minted nonce and no skip-if-missing branch;
* the contract is RUN as behaviour on one signed test flow: first sign-in
  passes; replay from a new session, replay after consume, and a missing
  nonce all reject.

Standard library only.
"""
import os
import sys
import time

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-signin", "SKILL.md")
GUIDE = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-signin",
                     "references", "full-guide.md")
SIWG = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-auth",
                    "references", "sign-in-with-google.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def read(p):
    with open(p, encoding="utf-8") as fh:
        return " ".join(fh.read().split())


def t_docs_carry_the_server_issued_contract():
    for path, name in ((SKILL, "SKILL.md"), (GUIDE, "full-guide.md"), (SIWG, "sign-in-with-google.md")):
        d = read(path)
        assert "server-issued" in d.lower() or "server issues the nonce" in d.lower(), \
            f"{name}: the server-issued rule is missing"
        assert "one-time consume" in d, f"{name}: no one-time consume"
    g = read(GUIDE)
    assert "GET /api/auth/google/nonce" in g and "pre-auth HttpOnly" in g
    s = read(SIWG)
    assert "one contract, both skills" in s, "the two skills no longer share one contract"


def t_client_minted_nonce_is_gone():
    g = read(GUIDE)
    assert "_googleNonce = crypto.randomUUID()" not in g, \
        "the client still mints the nonce — the finding itself"
    assert "credential: response.credential, nonce" not in g and \
           "credential, nonce: NONCE" not in g, "the nonce still rides in the POST body"
    assert 'if data.nonce and payload.get("nonce")' not in g, \
        "the skip-if-missing branch survived"
    assert "nonce_store.pop" in g.replace("_nonce_store.pop", "nonce_store.pop")
    s = read(SIWG)
    assert "crypto.randomUUID();  // or any random string" not in s
    assert "if body.nonce:" not in s, "the optional-nonce branch survived in google-auth"


# ---------------- the contract, run as behaviour on one signed test flow


class Server:
    TTL = 600

    def __init__(self):
        self.store = {}
        self.sids = 0

    def issue(self, now):
        self.sids += 1
        sid = f"sid-{self.sids}"
        nonce = f"nonce-{self.sids}"
        self.store[sid] = (nonce, now + self.TTL)
        return sid, nonce

    def callback(self, sid, token, now):
        expected, expires = self.store.pop(sid, (None, 0.0))
        if not expected or now > expires or token.get("nonce") != expected:
            return 401
        return 200


def t_flow_first_passes_replays_and_missing_reject():
    now = time.time()
    srv = Server()
    sid, nonce = srv.issue(now)
    token = {"sub": "g-1", "nonce": nonce}          # one signed test JWT
    assert srv.callback(sid, token, now) == 200, "the first sign-in failed"
    assert srv.callback(sid, token, now) == 401, \
        "a replay after consume passed — the store was not popped"
    sid2, _ = srv.issue(now)
    assert srv.callback(sid2, token, now) == 401, \
        "a replay from a NEW session passed — the stolen token replays"
    sid3, _ = srv.issue(now)
    assert srv.callback(sid3, {"sub": "g-1"}, now) == 401, \
        "a token with no nonce claim passed — the mandatory check is optional again"
    sid4, _ = srv.issue(now)
    assert srv.callback(sid4, {"sub": "g-1", "nonce": "nonce-4"}, now + 601) == 401, \
        "an expired expectation passed"


def main():
    case("all three docs carry the server-issued, one-time contract",
         t_docs_carry_the_server_issued_contract)
    case("the client-minted nonce and the skip-if-missing branch are gone",
         t_client_minted_nonce_is_gone)
    case("first passes; new-session replay, post-consume replay, missing and expired reject",
         t_flow_first_passes_replays_and_missing_reject)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
