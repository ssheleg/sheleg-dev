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

## Port implementation and focused results

[Helper identity](helper-identity.json) equals the canonical file byte-for-byte.
[Canonical independent review](canonical-independent-review.json) is source27b7e9
evidence, not independent acceptance of this owner adapter. Runtime package
version stays unchanged. [Dry-run payload readback](payload-parity.json) confirms
every included file's bytes match this owner's accepted base (46 SEO/68 dev files);
no package archive was published and temporary npm cache was removed.

`python3 -B test/audit_regressions/fw07_scratch_lock.py` passes
[30 controls](focused30.txt), exit0. `python3 -B test/validate.py` passes
[structural validation](structural.txt), exit0; the isolated checkout explicitly
discloses routed-trigger umbrella observation as unlooked. New regressions join
the existing `test:audit` glob, already part of the owner aggregate/CI.

The [first fixture run](first-fixture-failure.txt) failed because its positive
listing assertion was copied with TP's property-check suffix. These owners list
negative self-tests without that suffix. The common assertion now checks actual
negative-self-test listing and exit0; unsafe-lock refusal still requires exit1
and the admission diagnostic. No production guard was weakened.

The first structural run rejected the new dated receipt as unclassified;
[output](structural-first-failure.txt) is retained. Adding this exact dated source
receipt to DATED_RECORDS corrects its classification, without widening the
classification rule. Context-managed fixtures were removed on both failed and
passing runs. No public scratch or lock was touched by this owner.

Next: independent owner-adapter review, required serialized aggregate, frozen
candidate promotion with genuine checks and normal merge. No full local suite
or hosted/release acceptance has run in this slice.

## Independent owner acceptance

[Independent frozen-source review](owner-independent-review.json) accepts SEO
d6c87c3 and dev366a2d3 adapters, exact helper identity and the dev dated-receipt
classification. It independently replayed30 controls per owner (SEO2.22seconds,
dev1.34seconds), exit0, using owned namespaces only. This is bounded source
acceptance; mandatory owner aggregate before PR remains queued behind the
coordinator's active release/full-suite slot. No public negative suite was run.
