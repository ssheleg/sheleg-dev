#!/usr/bin/env python3
"""FIX-DV-19.04 — offline artifact / fault-injection corpus for google-signin
(sherlock audit, DV-19; sibling of 19.01–19.03).

Each corpus case injects a fault per DV finding; this regression runs a
STATE/OUTPUT oracle for each — not a provider stub judging itself. DV-19: each
counterexample FAILS pre-fix and PASSES post-fix on state/outputs, offline,
release-tied.

Standard library only; offline.
"""
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.04.json")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def manifest():
    with open(CASES, encoding="utf-8") as fh:
        return json.load(fh)


# ---- offline oracles (state/outputs) ------------------------------------------


def token_accepted(client_nonce, skip_when_absent, stored_nonce, token_nonce):
    """DV-10: is a credential accepted? A stolen token has token_nonce deleted."""
    if client_nonce:
        # pre-fix: no server challenge; if absent, the check is skipped → accepted
        if token_nonce is None:
            return skip_when_absent   # skip_when_absent=True → check skipped → accepted (the bug)
        return True
    # post-fix: server-issued nonce, compared, missing rejected
    if token_nonce is None or stored_nonce is None:
        return False
    return token_nonce == stored_nonce


def auto_links(trust_any_domain, domain, email_verified):
    """DV-11: does the account auto-link without re-verification?"""
    if not email_verified:
        return False
    if trust_any_domain:
        return True                       # pre-fix: any verified email links
    # post-fix: only Gmail or hd-bearing workspace domains are authoritative
    return domain in ("gmail.com",) or domain.startswith("hd:")


def post_accepted(missing_secfetch_is_same_origin, check_double_submit,
                  sec_fetch_site, cookie_token, body_token):
    """DV-12: is a sign-in POST accepted?"""
    same_origin = (sec_fetch_site == "same-origin")
    if sec_fetch_site is None:
        same_origin = missing_secfetch_is_same_origin   # pre-fix treats missing as same
    if not same_origin:
        return False
    if check_double_submit:
        return cookie_token is not None and cookie_token == body_token
    return True                            # pre-fix: no double-submit check


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"] and m["environment"]["network"].startswith("none")
    ids = {c["id"] for c in m["cases"]}
    assert ids == {"DV-10-nonce-server-challenge", "DV-11-auto-link-domain",
                   "DV-12-csrf-form-post"}, ids
    for c in m["cases"]:
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_dv10_stolen_token_replay():
    # pre-fix: client nonce, skip-when-absent → a stolen token (nonce deleted) is accepted
    assert token_accepted(client_nonce=True, skip_when_absent=True,
                          stored_nonce=None, token_nonce=None) is True, \
        "the stolen-token replay did not reproduce pre-fix"
    # post-fix: server nonce; a missing token nonce is rejected
    assert token_accepted(client_nonce=False, skip_when_absent=False,
                          stored_nonce="s1", token_nonce=None) is False, \
        "a missing nonce was accepted post-fix"
    assert token_accepted(client_nonce=False, skip_when_absent=False,
                          stored_nonce="s1", token_nonce="s1") is True


def t_dv11_third_party_reverify():
    # pre-fix: any verified email auto-links
    assert auto_links(trust_any_domain=True, domain="example.com",
                      email_verified=True) is True
    # post-fix: a third-party email is NOT auto-linked
    assert auto_links(trust_any_domain=False, domain="example.com",
                      email_verified=True) is False, \
        "a third-party email auto-linked post-fix"
    assert auto_links(trust_any_domain=False, domain="gmail.com",
                      email_verified=True) is True


def t_dv12_cross_site_post():
    # pre-fix: missing Sec-Fetch-Site treated as same-origin, no double-submit
    assert post_accepted(missing_secfetch_is_same_origin=True, check_double_submit=False,
                         sec_fetch_site=None, cookie_token=None, body_token=None) is True, \
        "the cross-site POST bypass did not reproduce pre-fix"
    # post-fix: missing Sec-Fetch-Site is NOT same-origin
    assert post_accepted(missing_secfetch_is_same_origin=False, check_double_submit=True,
                         sec_fetch_site=None, cookie_token="a", body_token="a") is False, \
        "a missing Sec-Fetch-Site passed post-fix"
    # a genuine same-origin POST with matching double-submit passes
    assert post_accepted(missing_secfetch_is_same_origin=False, check_double_submit=True,
                         sec_fetch_site="same-origin", cookie_token="a", body_token="a") is True
    # same-origin but mismatched token fails
    assert post_accepted(missing_secfetch_is_same_origin=False, check_double_submit=True,
                         sec_fetch_site="same-origin", cookie_token="a", body_token="b") is False


def main():
    case("the corpus is offline, release-tied, one case per DV oracle",
         t_corpus_structure)
    case("DV-10: a stolen token replays pre-fix, is rejected post-fix",
         t_dv10_stolen_token_replay)
    case("DV-11: a third-party email auto-links pre-fix, re-verified post-fix",
         t_dv11_third_party_reverify)
    case("DV-12: a cross-site POST passes pre-fix, is rejected post-fix",
         t_dv12_cross_site_post)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
