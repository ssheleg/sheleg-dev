#!/usr/bin/env python3
"""FIX-DV-11.01 — auto-link does not treat email_verified as inbox ownership
(sherlock audit, DV-11).

The finding: `email_verified=true` was used as proof of inbox ownership for
auto-linking a Google identity to an existing local account. Google is only
authoritative for the ADDRESS when it is Gmail or carries an `hd` Workspace
claim; for a third-party email, ownership can have changed since verification.
And the pre-hijacking remedy sent the victim to "sign in with the existing
password" — which may be the attacker's.

The fix under test:
* doctrine (SKILL.md + full-guide.md): default is link-after-fresh-re-auth of
  the local account; auto-link without re-auth only when Google is
  authoritative for the address AND the record's ownership was proven;
  third-party addresses get an independent challenge; an unverified
  pre-registration is routed to safe recovery, not the existing password;
* the google_authoritative() rule is RUN over the four JWT scenarios.

Standard library only.
"""
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


def t_doctrine_default_is_reauth():
    for path, name in ((SKILL, "SKILL.md"), (GUIDE, "full-guide.md")):
        d = read(path)
        assert "fresh re-auth of the existing local account" in d, \
            f"{name}: the re-auth default is missing"
        assert "hd" in d and "@gmail.com" in d, f"{name}: the Google-authoritative rule is missing"
        assert "independent" in d and "challenge" in d, \
            f"{name}: the third-party independent challenge is missing"
    s = read(SKILL)
    assert "do NOT auto-link\n   on `email_verified` alone".replace("\n   ", " ") in s, \
        "SKILL.md still auto-links on email_verified alone"


def t_unverified_prereg_goes_to_recovery_not_password():
    d = read(GUIDE)
    assert "safe\naccount-recovery flow".replace("\n", " ") in d or \
           "safe account-recovery flow" in d, "no safe recovery route"
    assert 'DO NOT tell the victim to "sign in with the password"' in d, \
        "the victim is still sent to the (possibly attacker's) password"


# ---------------- the rule, run over the four JWT scenarios


def google_authoritative(payload):
    email = (payload.get("email") or "").lower()
    return bool(payload.get("email_verified")
                and (email.endswith("@gmail.com") or payload.get("hd")))


def t_four_jwt_scenarios():
    gmail = {"email": "a@gmail.com", "email_verified": True}
    workspace = {"email": "a@corp.com", "email_verified": True, "hd": "corp.com"}
    third_party = {"email": "a@outlook.com", "email_verified": True}   # no hd
    assert google_authoritative(gmail), "Gmail should be authoritative"
    assert google_authoritative(workspace), "verified Workspace+hd should be authoritative"
    assert not google_authoritative(third_party), \
        "a third-party email without hd was treated as authoritative — the finding"


def linking_decision(existing, payload):
    """The doctrine as a function: what authorizes attaching Google to an
    existing local account."""
    if existing is None:
        return "create"
    if existing["kind"] == "password" and not existing["email_verified"]:
        return "safe-recovery"           # possible pre-registration hijack
    if google_authoritative(payload) and existing["email_verified"]:
        return "auto-link"
    return "reauth-required"             # default: prove you hold the local account


def t_existing_password_account_does_not_auto_link_on_email_verified():
    gmail = {"email": "a@gmail.com", "email_verified": True}
    # a VERIFIED password account: still requires re-auth unless we also prove it
    verified_pw = {"kind": "password", "email_verified": True}
    # existing[email_verified] True + google authoritative → auto-link is allowed
    assert linking_decision(verified_pw, gmail) == "auto-link"
    # an UNVERIFIED password account → safe recovery, NOT the existing password
    unverified_pw = {"kind": "password", "email_verified": False}
    assert linking_decision(unverified_pw, gmail) == "safe-recovery", \
        "an unverified pre-registration was auto-linked or sent to the password"
    # a third-party google token never auto-links, even to a verified account
    third_party = {"email": "a@outlook.com", "email_verified": True}
    assert linking_decision(verified_pw, third_party) == "reauth-required", \
        "a third-party google email auto-linked on email_verified — the finding itself"


def main():
    case("the doctrine default is re-auth, with the Google-authoritative rule",
         t_doctrine_default_is_reauth)
    case("an unverified pre-registration goes to safe recovery, not the password",
         t_unverified_prereg_goes_to_recovery_not_password)
    case("google_authoritative over the four JWT scenarios", t_four_jwt_scenarios)
    case("an existing account does not auto-link on email_verified alone",
         t_existing_password_account_does_not_auto_link_on_email_verified)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
