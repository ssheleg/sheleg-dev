## What and why

<!-- What changes, and what problem it solves. Link the issue if there is one. -->

## Evidence

<!-- Paste what you ran and what it printed. Both are required for any change. -->

```
npm test    # python3 test/validate.py, node test/moneygate_test.js, node test/fixtures_test.js
```

<!--
The whole gate, not one third of it. Until 2026-08-20 this block asked for
`python3 test/validate.py` alone, so a contributor who pasted exactly what was asked for
supplied evidence about the structural validator and nothing about the money gate or the
assertion packs — and the reviewer had no way to see the gap.
-->

## Checklist

- [ ] Every check above passes locally
- [ ] Behavior change is reflected in `README.md` and in the skill's own docs
- [ ] `CHANGELOG.md` has an entry for this change
- [ ] If versions moved: `marketplace.json`, `plugin.json`, `package.json` and the top `CHANGELOG.md` entry all agree
- [ ] A new `references/` file is linked from its `SKILL.md` — the validator fails a dangling link and an unlinked file alike
