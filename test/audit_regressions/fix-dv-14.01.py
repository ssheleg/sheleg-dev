#!/usr/bin/env python3
"""FIX-DV-14.01 — the unconditional noscript pixel contradicted the
consent-gated architecture (sherlock audit, DV-14).

The finding: the Meta `<noscript>` <img> fired unconditionally — so a
JS-disabled visitor with no consent produced a Meta request, despite the
stack's promise that Meta is not rendered until consent. And the same body's
GA4 `G-` config carried `allow_enhanced_conversions: true`, which a later
section forbids on a `G-` tag (it belongs on the Google Ads `AW-` tag).

The fix under test (ad-tracking/SKILL.md):
* the noscript Meta pixel is emitted server-side ONLY behind a
  server-verifiable consent, or omitted;
* the GA4 `G-` config no longer carries allow_enhanced_conversions;
* a static template check refuses both mistakes — modelled here as a linter
  run over every snippet in the skill.

Standard library only.
"""
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "ad-tracking", "SKILL.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def text():
    with open(SKILL, encoding="utf-8") as fh:
        return fh.read()


def code_blocks():
    return re.findall(r"```[a-z]*\n(.*?)```", text(), re.S)


# ---------------- the static template checks, run over the skill's own snippets


def enhanced_on_g_tag(block):
    """A gtag('config', 'G-…', {... allow_enhanced_conversions ...}) is the mistake."""
    for m in re.finditer(r"gtag\(\s*'config'\s*,\s*'([A-Z]+-[^']*)'\s*,\s*\{([^}]*)\}", block):
        tag, opts = m.group(1), m.group(2)
        if tag.startswith("G-") and "allow_enhanced_conversions" in opts:
            return True
    return False


def ungated_noscript_meta(block):
    """A <noscript> Meta pixel not wrapped in a server-side consent condition."""
    if "facebook.com/tr" not in block or "<noscript" not in block:
        return False
    # gated if a server-side consent guard appears in the same block
    gated = ("consent_cookie_verified" in block or "consent.ad_storage" in block
             or re.search(r"\{%\s*if .*consent", block))
    return not gated


def t_no_snippet_puts_enhanced_on_a_g_tag():
    offenders = [b for b in code_blocks() if enhanced_on_g_tag(b)]
    assert not offenders, "a G- config still carries allow_enhanced_conversions (the finding)"


def t_no_ungated_noscript_meta_pixel():
    offenders = [b for b in code_blocks() if ungated_noscript_meta(b)]
    assert not offenders, "an unconditional noscript Meta pixel survived — it fires without consent"


def t_doctrine_states_the_rules():
    d = " ".join(text().split())
    assert "server-verifiable consent" in d, "the server-verifiable-consent rule is missing"
    assert "Omit it" in d or "omit the noscript" in d.lower(), "the omit-if-unverifiable option is missing"
    assert "EXECUTABLE templates" in d, "the executable-template origin is not stated"
    assert "a static check refuses the two\nmistakes".replace("\n", " ") in d or \
           "static check refuses the two mistakes" in d, "the static-check promise is missing"


def t_the_linter_catches_a_planted_defect():
    # prove the check has teeth: it must flag the exact snippets the finding described
    bad_g = "gtag('config', 'G-XXXX', { allow_enhanced_conversions: true });"
    assert enhanced_on_g_tag(bad_g), "the G-tag linter does not catch the planted flag"
    good_g = "gtag('config', 'AW-XXXX', { allow_enhanced_conversions: true });"
    assert not enhanced_on_g_tag(good_g), "the linter false-flags the AW- tag"
    bad_ns = ('<noscript><img src="https://www.facebook.com/tr?id=P&ev=PageView&noscript=1"/>'
              '</noscript>')
    assert ungated_noscript_meta(bad_ns), "the noscript linter does not catch an ungated pixel"
    gated_ns = ('{% if consent_cookie_verified %}<noscript><img '
                'src="https://www.facebook.com/tr?id=P"/></noscript>{% endif %}')
    assert not ungated_noscript_meta(gated_ns), "the linter false-flags a gated pixel"


def main():
    case("no snippet puts allow_enhanced_conversions on a G- tag",
         t_no_snippet_puts_enhanced_on_a_g_tag)
    case("no unconditional noscript Meta pixel remains", t_no_ungated_noscript_meta_pixel)
    case("the doctrine states server-consent / omit / executable-template / static-check",
         t_doctrine_states_the_rules)
    case("the static checks catch their planted defects", t_the_linter_catches_a_planted_defect)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
