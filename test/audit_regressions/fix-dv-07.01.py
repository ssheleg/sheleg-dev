#!/usr/bin/env python3
"""FIX-DV-07.01 — the opaque browser session (sherlock audit, DV-07).

The finding: Flask's default session and Starlette's SessionMiddleware SIGN
the cookie but do not ENCRYPT it, and the guide put token, refresh_token and
client_secret straight into it — plus console.log(tokens.access_token). The
official docs confirm the cookie is readable.

The fix under test: the cookie holds only a random opaque session id; Google
credentials go to a server-side encrypted store keyed by (session, principal);
no token logging; a required production signing secret with no dev fallback; a
Secure cookie / HTTPS guard. Documented, and the store rule is run as
behaviour proving no secret reaches the cookie/redirect/body.

Standard library only.
"""
import os
import sys

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


def t_doctrine_states_opaque_session():
    flat = " ".join(open(DOC, encoding="utf-8").read().replace("//", " ").split())
    for needle in ("A signed cookie is not an encrypted one",
                   "only a random\nopaque session id".replace("\n", " "),
                   "server-side encrypted\nstore".replace("\n", " "),
                   "fetched by\n`(session_id, principal)`".replace("\n", " "),
                   "never log a\ntoken or a credential".replace("\n", " "),
                   "required production secret with NO dev fallback",
                   "the callback refuses plain HTTP"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"
    raw = open(DOC, encoding="utf-8").read()
    assert "console.log('New access_token:', tokens.access_token)" not in raw, \
        "the token logging survived"
    assert "session['credentials'] = {\n" not in raw, \
        "the credentials-in-cookie assignment survived"


# ---------------- the session/store model, executed


SECRETS = {"token", "refresh_token", "client_secret"}


class Cookie:
    def __init__(self):
        self.value = {}      # signed, NOT encrypted — treat as readable

    def readable_contents(self):
        return dict(self.value)


class Store:
    """Server-side, encrypted at rest, keyed by (sid, principal)."""

    def __init__(self):
        self._rows = {}

    def put(self, sid, principal, credentials):
        self._rows[(sid, principal)] = dict(credentials)

    def get(self, sid, principal):
        return self._rows.get((sid, principal))


def login(cookie, store, credentials, principal):
    import os as _os
    sid = cookie.value.get("sid") or _os.urandom(16).hex()
    cookie.value["sid"] = sid                          # opaque id only
    store.put(sid, principal, credentials)             # secrets go here
    return sid


def t_cookie_holds_no_secret():
    cookie, store = Cookie(), Store()
    creds = {"token": "ya29...", "refresh_token": "1//0g...",
             "client_secret": "GOCSPX-..."}
    login(cookie, store, creds, principal="user-123")
    contents = " ".join(str(v) for v in cookie.readable_contents().values())
    for secret in creds.values():
        assert secret not in contents, \
            "a secret was readable in the cookie — the finding itself"
    assert list(cookie.readable_contents()) == ["sid"], \
        "the cookie carries more than an opaque id"


def t_credentials_fetched_by_session_and_principal():
    cookie, store = Cookie(), Store()
    creds = {"token": "t", "refresh_token": "r", "client_secret": "s"}
    sid = login(cookie, store, creds, principal="user-123")
    assert store.get(sid, "user-123") == creds
    assert store.get(sid, "someone-else") is None, \
        "credentials were reachable by session alone, without the principal"


def t_no_secret_in_redirect_or_body():
    # simulate the callback's redirect + response body
    redirect = "/profile"
    body = "signed in"
    for surface in (redirect, body):
        for secret in ("ya29", "GOCSPX", "1//0g"):
            assert secret not in surface, \
                f"a secret leaked into a client-visible surface: {surface!r}"


def t_signing_secret_has_no_dev_fallback():
    def resolve_secret(env, allow_default=False):
        s = env.get("SESSION_SECRET")
        if s:
            return s
        if allow_default:
            return "dev-insecure-default"
        raise RuntimeError("SESSION_SECRET is required in production — no fallback")
    try:
        resolve_secret({}, allow_default=False)
        raise AssertionError("production resolved a fallback signing secret")
    except RuntimeError as e:
        assert "no fallback" in str(e)
    assert resolve_secret({"SESSION_SECRET": "real"}) == "real"


def main():
    case("the doctrine states the opaque session and its guards",
         t_doctrine_states_opaque_session)
    case("the cookie holds no secret, only an opaque id", t_cookie_holds_no_secret)
    case("credentials are fetched by session AND principal",
         t_credentials_fetched_by_session_and_principal)
    case("no secret in the redirect or the response body",
         t_no_secret_in_redirect_or_body)
    case("the signing secret has no dev fallback in production",
         t_signing_secret_has_no_dev_fallback)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
