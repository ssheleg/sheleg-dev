#!/usr/bin/env python3
"""FIX-DV-15.01 — the URL credential scrubber catches userinfo, path and query
(sherlock audit, DV-15).

The finding, from running the reference code: the scrubber's regex required a
NON-EMPTY username, so `redis://:AUDIT_FAKE_PASSWORD@host` walked through
unredacted; a Telegram token in the PATH (`/bot<id>:<token>/`) and a credential
in the QUERY (`?access_token=…`) were never matched.

The fix under test extracts the scrubber code FROM scrubbing.md and runs it:
* an empty-username userinfo password is redacted;
* a Telegram bot token in the path is redacted;
* an access token in the query is redacted;
* the encoded/normal `user:pw@` case still redacts;
* a safe URL (a lone user, a non-secret query key) keeps its useful shape.

Standard library only.
"""
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "error-tracking",
                   "references", "scrubbing.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def load_scrub_text():
    """Extract the scrub_text definition (and its regexes) from the doc and exec
    it, so the test runs the code the skill actually ships."""
    text = open(DOC, encoding="utf-8").read()
    block = None
    for m in re.finditer(r"```python\n(.*?)```", text, re.S):
        if "def scrub_text" in m.group(1) and "_URL_USERINFO" in m.group(1):
            block = m.group(1)
            break
    assert block, "the scrub_text code block was not found in scrubbing.md"
    ns = {}
    exec(compile(block, "scrubbing.md", "exec"), ns)  # noqa: S102 — runs the shipped code
    return ns["scrub_text"]


SCRUB = load_scrub_text()


def t_empty_username_redis_password():
    out = SCRUB("redis://:AUDIT_FAKE_PASSWORD@host:6379")
    assert "AUDIT_FAKE_PASSWORD" not in out, "the empty-username redis password leaked — the finding"
    assert "redis://" in out and "@host:6379" in out, "the useful URL shape was destroyed"


def t_bot_token_in_path():
    out = SCRUB("https://api.telegram.org/bot123456:AUDIT_FAKE_TOKEN_abcDEF/sendMessage")
    assert "AUDIT_FAKE_TOKEN_abcDEF" not in out, "the Telegram bot token in the path leaked"
    assert "/sendMessage" in out and "api.telegram.org" in out, "the path shape was destroyed"


def t_access_token_in_query():
    out = SCRUB("https://api.example.com/x?access_token=AUDIT_FAKE_TOKEN&q=1")
    assert "AUDIT_FAKE_TOKEN" not in out, "the query access_token leaked"
    assert "q=1" in out, "a non-secret query param was scrubbed"


def t_normal_userinfo_still_redacts():
    out = SCRUB("postgres://u4fc:SUPERSECRETPW@host.rds.amazonaws.com:5432/db")
    assert "SUPERSECRETPW" not in out, "the normal user:pw@ password leaked"
    assert "u4fc" in out and "host.rds.amazonaws.com" in out, "user/host were lost"


def t_safe_url_keeps_shape():
    for safe in ("postgres://appuser@db.host/mydb", "https://example.com/search?q=hello",
                 "https://cdn.example.com/assets/app.js"):
        assert SCRUB(safe) == safe, f"a safe URL was altered: {safe!r} -> {SCRUB(safe)!r}"


def main():
    case("an empty-username redis password is redacted", t_empty_username_redis_password)
    case("a Telegram bot token in the path is redacted", t_bot_token_in_path)
    case("an access token in the query is redacted", t_access_token_in_query)
    case("a normal user:pw@ password is still redacted", t_normal_userinfo_still_redacts)
    case("a safe URL keeps its useful shape", t_safe_url_keeps_shape)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
