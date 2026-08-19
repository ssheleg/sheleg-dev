# Merge log

Appended by `agent-sync`, not written by hand. `.claude/agent-sync.json` →
`mergeLog.file` points here with a 7-day retention, and until 2026-08-20 it pointed at
this path while the file did not exist — a configured destination nothing could write to,
in the config whose whole job is to keep two agents from overwriting each other.

`test/validate.py` → `check_agent_sync_config_paths_resolve` now requires every path in
that config to resolve, and `DATED_RECORDS` classifies this file as a record rather than a
live document: a merge entry names the branches and files of a merge that already happened,
including paths that have since moved.

<!-- entries below, newest first -->
