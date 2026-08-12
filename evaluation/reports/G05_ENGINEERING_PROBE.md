# G05 Bounded Engineering Probe

Date: 2026-08-12
Base revision: `4b6b7e4`

Command: `.venv/bin/python scripts/accept_g05.py`

Result:

- Visual research adapter: 16/16 successful frame requests with 4 local threads.
- P50 provider duration: 8 ms.
- P95 provider duration: 17 ms (latest full-check run; host scheduling makes this non-gating).
- Production authority: false.
- Qualification matrix: 12 checks; 6 passed, 4 blocked, 2 not evaluated.

This bounded probe tests adapter thread safety and deterministic qualification loading only. It is
not the required long-video/multi-project workload, does not exercise the full Object Store/
PostgreSQL/Temporal path, and does not close the capacity or Worker-restart blockers.
