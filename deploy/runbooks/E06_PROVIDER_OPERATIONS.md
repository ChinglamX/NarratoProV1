# E06 Provider Operations Runbook

## Scope

Speech and Visual Observation providers only. This runbook never authorizes Fact/Story creation,
L2 routing, or Release.

## Preconditions

1. Resolve the exact Provider Package, model checksum, code/weight licenses, config, resource
   profile, benchmark report and routing pointer.
2. Confirm Automation `L1`, Confidence `shadow`, and source-asset rights/data-residency policy.
3. Do not start a provider whose package is `research` under a production policy.

## Triage

| Signal | Immediate action | Recovery evidence |
|---|---|---|
| unavailable/health | stop new shards; use explicit unavailable/manual | health, raw failure, no empty success |
| timeout/rate limit | preserve idempotency key; bounded retry/backoff | one committed raw artifact |
| RAM/Metal/OOM | reduce micro-batch once; quarantine repeated input | resource estimate and failure event |
| checksum/rights drift | block provider immediately | package diff and rights review |
| S0/severe regression | return routing pointer to last approved package | CAS audit and shadow comparison |
| Worker lost | restart compatible build; allow Temporal replay | history replay and artifact idempotency |

## Canary

Use `deploy/provider-routing/e06-canary-policy.json`. Shadow outputs have no routing authority.
Canary promotion requires every configured quality, severe-error, resource, rights and resilience
check plus human change approval. Existing Artifacts remain immutable and separately attributable.

## Rollback

1. Stop admitting new shards for the candidate.
2. CAS the routing pointer to the last approved Provider Package; do not edit generated Artifacts.
3. Mark candidate observations and calibration scope drifted/invalid for routing.
4. Resume only L1/Shadow work and validate queue drain, health and one golden case.
5. Open a structured QualityEvent/Correction dataset entry; do not train or publish automatically.

## Known G05 blockers

The current matrix at `evaluation/qualification/e06_g05.json` is not production-qualified. Missing
model rights, real series-isolated benchmarks, long-series/concurrent capacity, exact Speech/Visual
Worker interruption acceptance and complete resource/cost evidence must be closed before approval.
