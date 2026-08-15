# E11 Render and Release Runbook

1. Preflight exact Conformed Timeline, Mixed Audio, ASS, Platform and toolchain refs.
2. Reject any upstream unresolved conflict, missing blob/checksum, unknown rights or profile omission.
3. Compile deterministic operations/cache keys; Render Worker uses admission, heartbeat and bounded retry.
4. Probe the complete output; compare duration, streams, codec, dimensions, fps, loudness and True Peak.
5. Run sync, black/freeze/silence, subtitle geometry and proxy/final parity checks.
6. Build a complete per-asset Rights Manifest for the intended platform, territory and date.
7. Run offline review in required order; every finding carries timecode/artifact evidence.
8. Any Technical, Rights or Quality blocker forces Reject regardless of weighted score.
9. Gate 3 requires a human `release_approver`; service accounts and automation can never approve.
10. Publish only the exact FinalCandidate/checksum; corrections create successors and repeat preflight.
11. Time-base discipline (E09 ADR-051 lesson): MasterTimeline track ranges are microsecond-based (rate 1_000_000) while the timeline duration may use a coarser rate (e.g. 121/4 = 30.25s). RenderPlan operations carry each item's raw range; consumers must compare via `seconds`, never by raw value across different rates. Deterministic compilation is verified: identical inputs produce identical RenderPlan checksums.
