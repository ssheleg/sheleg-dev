# Security

## What this skill actually does on your machine

`sheleg-dev` is documentation plus one small Python script. Installed, it is:

| Component | Runtime behavior |
|---|---|
| `SKILL.md` + `references/*.md` | Text. Read by the agent, executes nothing. |
| `scripts/page_audit.py` | Runs only when you or the agent invokes it. Python **standard library only** — no dependencies, no install step. |
| `commands/`, `cursor/rules/` | Text read by the host agent. |
| `bin/sheleg-dev.js` (npm installer) | Copies the skill directory and the slash command into `~/.claude/`. No network, no post-install script. |

There is no telemetry, no analytics, no phone-home, and nothing writes outside
the paths above.

## Network behavior of `page_audit.py`

- Plain `GET` requests, **http and https only** — any other scheme (`file://`,
  `ftp://`, `gopher://`, …) is refused before a request is made, and a redirect
  that leaves http(s) is refused too.
- Only to URLs **you** pass via `--url` / `--url-list`. In `--file` mode it makes
  no requests at all, which is how the test suite runs.
- No cookies, no credentials, no auth headers; a plain User-Agent that identifies
  the tool.
- Bounded: `--timeout` (default 20s) and `--max-bytes` (default 5 MB). A declared
  content type that is not HTML/XHTML/XML is refused rather than parsed.
- Read-only: results go to stdout. The script never writes a file. The only files
  it ever **reads** are the two you name yourself (`--file`, `--url-list`).

## What the skill will not tell an agent to do

The audit procedure is explicitly **defensive**. Manipulative tactics —
cloaking, fabricated consensus networks, review manipulation, click-signal
spoofing, takedown abuse — appear only in `references/threats-and-defense.md`,
written as *detect and withstand*, and the skill's non-negotiables forbid
recommending them.

The procedure is also read-only by default: it will not submit forms, request
indexing, disavow links or change a live property without explicit approval in
the session.

## Reporting a problem

Open an issue at <https://github.com/ssheleg/sheleg-dev/issues>. If it is
sensitive, say so in the issue without the details and a private channel will be
arranged.

## Verifying for yourself

```bash
git clone https://github.com/ssheleg/sheleg-dev && cd sheleg-dev
python3 test/validate.py         # structure, version sync, references, links, anchors
python3 test/test_page_audit.py  # auditor behavior, offline fixtures + scheme guard
grep -rnE "urlopen|build_opener|opener\.open|socket|subprocess|os\.system|\beval\(|\bexec\(|\bopen\(" \
  plugins/sheleg-dev/skills/sheleg-dev/scripts/page_audit.py
```

The last command prints the auditor's entire I/O surface — six lines: the
`urllib.request` import, one comment, the opener that carries the scheme guard,
the one `opener.open(...)` call, and the two `open()` calls that read the file
paths you pass on the command line. No `subprocess`, no `os.system`, no `eval`,
no `exec`, no raw sockets. Everything else in `plugins/` is markdown.
