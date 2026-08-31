#!/usr/bin/env python3
"""Resolve every `$schema` this repository declares, and validate against what it serves.

    python3 test/check_schemas.py

ADOPTED from `telegram-dev/test/check_schemas.py` (shipped 2026-08-31 in its 0263b89),
whose family-wide sweep is what found the defect this file guards. Two things differ
from the original: the repository name in the User-Agent, and the note below about the
position the address sat in here. Everything else is the same file, because two
implementations of one idea is the defect this family keeps finding in its own history.

Deliberately NOT part of `npm test`. That suite is stdlib-only and offline by design,
so its `$schema` guard can only PIN addresses — it asserts that each manifest names,
AT ITS ROOT, the one schema right for its document type, and refuses both the dead
`claude-code-plugin.json` and the inert nested position. Pinning is not proof: an
address that resolved when it was pinned can stop resolving, and a document that
validated can drift out of the schema it declares. This is the half that looks.

What it would have caught here that a name check could not: v0.11.2 corrected the
address in `.claude-plugin/marketplace.json` while leaving it inside `plugins[0]`,
where `$schema` is inert. The document had no effective declaration at all, so there
was nothing for this script to fetch and nothing validating the marketplace — and the
tree read as fixed. A shape check and a resolution check answer different questions,
and this repository has now been wrong in both directions.

Both halves read `SCHEMA_FOR` from `test/validate.py`, so the address map has one home.
Two checks with two copies of a URL is how the copies disagree.

Exits 1 on the first thing it can prove wrong, and 2 when it cannot look at all —
a check that could not run must never read as one that ran and passed.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import ROOT, SCHEMA_FOR  # noqa: E402  (path set above)

TIMEOUT = 30
UA = "sheleg-dev-schema-check (+https://github.com/ssheleg/sheleg-dev)"


def fetch(url: str):
    """GET following redirects. Returns (final_url, parsed_json)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.geturl(), json.loads(resp.read().decode("utf-8"))


def main() -> int:
    try:
        import jsonschema
    except ImportError:
        print("CANNOT LOOK: jsonschema is not installed — `pip install jsonschema`.")
        print("Refusing to exit 0: a check that did not run is not a check that passed.")
        return 2

    problems: list[str] = []
    for rel, want in SCHEMA_FOR.items():
        path = Path(ROOT) / rel
        if not path.is_file():
            problems.append(f"{rel} is missing")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        declared = doc.get("$schema")
        if declared != want:
            # The offline guard owns this comparison; repeated here so this script
            # is honest when run alone against a tree that never met that guard.
            # `declared` is read at the ROOT deliberately — the nested copy this
            # repository shipped would make this None, which is the true answer.
            problems.append(f"{rel}: declares {declared!r} at its root, "
                            f"pinned map says {want!r}")
            continue

        try:
            final, schema = fetch(declared)
        except urllib.error.HTTPError as exc:
            problems.append(f"{rel}: {declared} -> HTTP {exc.code} "
                            f"(final {exc.url}) — the declared schema does not resolve")
            continue
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            print(f"CANNOT LOOK: fetching {declared} failed — {exc}")
            return 2

        title = schema.get("title", "(untitled)")
        print(f"  {rel}")
        print(f"    $schema  {declared}")
        print(f"    resolves 200 -> {final}")
        print(f"    title    {title!r}")

        validator = jsonschema.validators.validator_for(schema)
        try:
            validator.check_schema(schema)
        except jsonschema.exceptions.SchemaError as exc:
            problems.append(f"{rel}: the served schema is itself invalid — {exc.message}")
            continue
        errors = sorted(validator(schema).iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            for err in errors:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                problems.append(f"{rel}: {loc}: {err.message}")
        else:
            print("    validates against it")

    if problems:
        print("\nFAIL: declared schemas")
        for p in problems:
            print(f" - {p}")
        return 1
    print(f"\nOK: {len(SCHEMA_FOR)} declared schema(s) resolve and validate what declares them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
