# FW07 shared scratch-lock port — sheleg-dev

Frozen owner base `21e0c531a0fdd306aa8a8e408f5b8d34d9f9b369`. The canonical
[TP source27b7e9e](https://github.com/ssheleg/task-pipeline/commit/27b7e9ef5722a79fd314216af183eb4db3a8ec5a)
was independently accepted with30 owned-namespace controls and42 existing runner
controls. Its packet proves different TMPDIR locks do not serialize fixed /tmp
plants and canonical owner scratch destinations overlap.

This owner port will copy `test/negative_lock.py` byte-identically, adapt the
runner's lock acquisition only, and replay fixtures under owned directories.
No public negative suite/list invocation, published payload, version or tag change.
The same helper supplies one physical-/tmp identity, exclusive create/no-follow
open, private regular current-user single-link admission and whole-suite flock.
It never truncates, chmods, unlinks or steals a lock. Old versions and directly
invoked plants remain outside the new mechanism.

Acceptance: owner actual runner refuses unsafe owned lock before plants and lists
under healthy owned lock; different TMPDIR/owner-labelled processes contend on
one inode, release/retry works; unsafe file kinds/modes/identity refuse unchanged.
Helper hash and excluded payload identity will be recorded after implementation.
Source-only plan at this commit; focused port and independent review next.
