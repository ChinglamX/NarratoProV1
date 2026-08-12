# E07 Story Intelligence Runbook

1. Confirm E06 Provider Qualification and rights status before production input.
2. Inspect Identity conflicts; never auto-merge `same_candidate` edges.
3. Apply merge/split/name through preview and human correction API; retry stale versions only after reload.
4. Verify FactSet incomplete partitions and FusionConflict before Story workflow.
5. Inspect Event, State and Causal artifacts independently; temporal order is not causality.
6. Story Gate must reference exact Fact/Identity/Event/State/Causal/Story/Config/Model versions.
7. Do not approve incomplete/blocker packages. Strategy reads only `approved_story` pointer.
8. On correction, inspect InvalidationDecision and recompute explicit closure; never delete old artifacts.
9. Keep project/artifact IDs in trace/log only, not metric labels.
