#!/usr/bin/env python3
"""FIX-DV-07.02 — secret handling edges (sherlock audit, DV-07 leaf 2, on
FIX-DV-07.01).

The edges under test: a missing production signing secret FAILS CLOSED (no dev
fallback); logs are sanitized so no credential reaches a line; HTTPS is
mandatory and a credential-store failure is an auth failure, not a silent
proceed. Documented in google-auth SKILL.md and oauth2-web-server.md, and the
fail-closed / sanitize / store-failure rules are run as behaviour.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GA = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-auth")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def t_doctrine_states_the_edges():
    sk = " ".join(open(os.path.join(GA, "SKILL.md"), encoding="utf-8").read().split())
    for needle in ("Fail closed on a missing production secret",
                   "NO dev fallback",
                   "Logs are sanitized; a credential never reaches one",
                   "Redact by allow-list",
                   "HTTPS is mandatory and the credential store can fail",
                   "a credential-store read/write that FAILS is an auth\nfailure".replace("\n", " ")):
        assert needle in sk, f"SKILL.md no longer states {needle!r}"
    ref = " ".join(open(os.path.join(GA, "references", "oauth2-web-server.md"),
                        encoding="utf-8").read().replace("//", " ").split())
    assert "a credential-store read or write that FAILS is an\nauth failure".replace("\n", " ") in ref
    assert "missing in production is\n**fail-closed**".replace("\n", " ") in ref


# ---------------- the rules, executed


def resolve_secret(env, is_production):
    s = env.get("SESSION_SECRET")
    if s:
        return s
    if is_production:
        raise SystemExit("SESSION_SECRET is required in production — fail closed")
    return None                                   # dev may run without it


def sanitize(line, allow):
    """Allow-list redaction: only allow-listed keys survive; everything else is
    redacted, so an unforeseen credential key cannot leak."""
    return {k: (v if k in allow else "[REDACTED]") for k, v in line.items()}


def load_credentials(store, sid, principal):
    creds = store.get((sid, principal))
    if creds is None:
        raise PermissionError("credential store returned nothing — auth failure")
    return creds


def t_missing_prod_secret_fails_closed():
    try:
        resolve_secret({}, is_production=True)
        raise AssertionError("production booted without a signing secret")
    except SystemExit as e:
        assert "fail closed" in str(e)
    assert resolve_secret({"SESSION_SECRET": "real"}, True) == "real"
    assert resolve_secret({}, is_production=False) is None   # dev tolerated


def t_logs_are_sanitized_by_allow_list():
    line = {"event": "login", "user": "u-1", "access_token": "ya29...",
            "refresh_token": "1//0g", "client_secret": "GOCSPX"}
    out = sanitize(line, allow={"event", "user"})
    joined = " ".join(str(v) for v in out.values())
    for secret in ("ya29", "1//0g", "GOCSPX"):
        assert secret not in joined, "a credential survived sanitization"
    assert out["event"] == "login" and out["user"] == "u-1"


def t_store_failure_is_an_auth_failure():
    class Store:
        def __init__(self, rows):
            self.rows = rows

        def get(self, key):
            return self.rows.get(key)

    ok = load_credentials(Store({("sid", "p"): {"token": "t"}}), "sid", "p")
    assert ok == {"token": "t"}
    try:
        load_credentials(Store({}), "sid", "p")
        raise AssertionError("an empty store read proceeded as authenticated")
    except PermissionError:
        pass


def main():
    case("the doctrine states the secret-handling edges", t_doctrine_states_the_edges)
    case("a missing production secret fails closed", t_missing_prod_secret_fails_closed)
    case("logs are sanitized by allow-list", t_logs_are_sanitized_by_allow_list)
    case("a credential-store failure is an auth failure",
         t_store_failure_is_an_auth_failure)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
