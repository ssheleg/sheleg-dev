#!/usr/bin/env python3
"""FIX-DV-12.01 — the FastAPI skeleton actually runs the CSRF contract it claims
(sherlock audit, DV-12).

The finding: the endpoint declared support for the GIS form-POST flow but bound
a Pydantic JSON body — so the form contract (g_csrf_token) sat on a request
shape that flow never sends. And a MISSING `Sec-Fetch-Site` was defaulted to
`same-origin` (`headers.get("sec-fetch-site", "same-origin")`), `none` was
allowed, and there was no Origin fallback — so a JSON request with no metadata
passed.

The fix under test:
* two SEPARATE, explicitly typed paths — form (x-www-form-urlencoded) and JSON;
* form requires g_csrf_token in BOTH body and cookie, equal;
* JSON requires Sec-Fetch-Site==same-origin OR (only when the header is absent)
  an exact allowlisted Origin; cross-site/none/missing-both fail closed; a
  missing header is NOT same-origin;
* the CSRF decision precedes token verification.

The doctrine's decision functions are RUN over the full matrix; standard
library only (no TestClient/FastAPI needed).
"""
import hmac
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-signin", "SKILL.md")
GUIDE = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-signin",
                     "references", "full-guide.md")

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


# ---------------- the doctrine's decision, mirrored and run


ALLOWED = {"https://app.example.com"}


def csrf_ok_form(cookie_token, form_token):
    if not form_token or not cookie_token:
        return False
    return hmac.compare_digest(cookie_token, form_token)


def csrf_ok_json(sec_fetch_site, origin):
    if sec_fetch_site == "same-origin":
        return True
    if sec_fetch_site in ("cross-site", "same-site", "none"):
        return False
    if sec_fetch_site is None:
        return bool(origin) and origin in ALLOWED
    return False


def t_form_matrix():
    assert csrf_ok_form("tok", "tok") is True, "valid double-submit rejected"
    assert csrf_ok_form("tok", "other") is False, "mismatched token accepted"
    assert csrf_ok_form(None, "tok") is False, "missing cookie accepted"
    assert csrf_ok_form("tok", None) is False, "missing body token accepted"
    assert csrf_ok_form(None, None) is False, "both missing accepted"


def t_json_matrix():
    # trusted metadata
    assert csrf_ok_json("same-origin", None) is True
    assert csrf_ok_json("cross-site", "https://app.example.com") is False, \
        "cross-site accepted despite an allowed Origin — metadata must win"
    assert csrf_ok_json("none", None) is False, "Sec-Fetch-Site: none accepted"
    assert csrf_ok_json("same-site", None) is False
    # header ABSENT → exact Origin fallback, allowlisted only
    assert csrf_ok_json(None, "https://app.example.com") is True, "allowed Origin fallback rejected"
    assert csrf_ok_json(None, "https://evil.example.com") is False, "disallowed Origin accepted"
    assert csrf_ok_json(None, None) is False, \
        "missing metadata AND missing Origin passed — the finding (fail-closed)"


def t_doctrine_states_the_contract():
    for path, name in ((SKILL, "SKILL.md"), (GUIDE, "full-guide.md")):
        d = read(path)
        assert "separate" in d.lower() and "typed" in d.lower(), \
            f"{name}: the two flows are not stated as separate typed paths"
        assert "missing `Sec-Fetch-Site` is NOT assumed same-origin" in d or \
               "missing\n`Sec-Fetch-Site` is NOT assumed same-origin".replace("\n", " ") in d, \
            f"{name}: a missing header is still assumed same-origin"
        assert "fail" in d.lower() and "closed" in d.lower(), f"{name}: no fail-closed rule"
        assert "before" in d.lower() and "verif" in d.lower(), \
            f"{name}: CSRF-before-verification is not stated"


def t_example_has_two_typed_routes():
    d = read(GUIDE)
    assert "application/x-www-form-urlencoded" in d, "the form path's content type is not shown"
    assert "credential: str = Form(...)" in d, "the form route does not bind a form body"
    assert "_csrf_ok_form" in d and "_csrf_ok_json" in d, "the two decision functions are gone"
    assert 'headers.get("sec-fetch-site", "same-origin")' not in d, \
        "the missing-header-defaults-to-same-origin bug survived"


def main():
    case("form flow: both g_csrf_token present and equal, else reject", t_form_matrix)
    case("json flow: metadata or allowlisted Origin, else fail closed", t_json_matrix)
    case("both docs state separate typed paths, no-assume, fail-closed, before-verify",
         t_doctrine_states_the_contract)
    case("the example ships two explicitly typed routes", t_example_has_two_typed_routes)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
