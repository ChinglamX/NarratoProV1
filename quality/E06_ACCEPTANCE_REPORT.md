# E06 Speech and Visual Observation Acceptance Report

Report Version: 1.0
Date: 2026-08-12
Scope: G01–G05 / R2 Observation slice

## Decision

Engineering recommendation: **REJECT production qualification; continue Research/L1 only.**

Human decision: **pending**

This is a completed qualification review with a negative result, not an unfinished or silently
approved production slice. E06 remains open until blockers are closed and the project owner signs a
new evidence-backed report.

## Proven

- Provider policy gateway, raw/normalized lineage and explicit unavailable.
- Series-isolated benchmark contracts/harness; synthetic fixtures do not declare thresholds.
- Typed Speech and Visual boundaries, Shadow Confidence and E06 scope isolation.
- Real local research calls: generated Mandarin Speech fixture and one local demo frame decode.
- Bounded local visual adapter probe: 16/16 requests with 4 threads, P50 8 ms/P95 17 ms; this is not
  the long-series/full-workflow capacity test.
- Unit/contract/workflow registration checks, Registry generation, static security and architecture.
- Canary/rollback policy, dashboard definition and provider incident runbook.

## Production blockers

1. No legal, representative, series-isolated Speech/Visual Development/Validation/Frozen Test pack.
2. FunASR checkpoint rights/checksum/commercial approval are incomplete.
3. OCR, semantic detector, tracker, face/appearance, embedding and VLM production providers are not
   selected, pinned, licensed or benchmarked.
4. Fixed Mac mini long-video/multi-project throughput, P50/P95 latency, peak RAM/Metal/disk,
   storage growth and cost-per-media-minute have not been measured end to end.
5. Exact Speech/Visual Workflow Worker kill/restart, repeated OOM, budget exhaustion and provider
   fallback have not completed runtime fault injection.
6. Dashboard definitions exist, but production metric export/alerts and operator drill are not yet
   deployment-qualified.

## Non-negotiable scope

- Automation remains L1; Confidence remains Shadow.
- Missing capability returns unavailable/manual; it never returns an empty success.
- Speaker cluster, Tracklet, Face and Embedding are not character identity.
- Observation is not Fact or Story; G05 creates neither.
- Release remains human and is outside E06.

## Re-entry criteria

Close every blocker in `evaluation/qualification/e06_g05.json`, rerun `make check`, run full
provider benchmark and failure/load acceptance on a frozen Mac mini Resource Profile, regenerate
this report, and obtain an explicit human signature. Thresholds must originate from the resulting
baseline and Quality Profile rather than this document.

## Human sign-off

- Decision: pending
- Name / Actor ID:
- Date:
- Qualification ArtifactRef:
- Notes:
