# Handoff — Canonical CJK Subtitle Fix

Handoff ID: 2026-08-18-cjk-subtitle-fix  
Date / Author: 2026-08-18 / Codex  
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Correct the user-reported garbled subtitles in canonical E11 output.  
Active Epic / Backlog ID: E10 K05 / E11 render qualification  
Starting State Version: 63

Completed:
- Confirmed UTF-8 input; isolated missing CJK fonts in Docker as root cause.
- Added explicit Heiti SC font mount and fail-closed missing-font behavior.
- Added deterministic 12-character CJK line wrapping after visual inspection found clipping.
- Canonical run `da464df7-3c93-4a38-acde-fed53191acec` passed render/QC; visual frame confirms readable, bounded Chinese captions.
- `make check`: 412 passed, 5 skipped, coverage 80.24%.

Human Review:
- Product owner reviewed the corrected full video and concluded “目前可接受”.

Not Completed:
- Portable redistributable production font remains to be selected/licensed.

Next Exact Step:
- Select a rights-cleared second source and execute the M5 repeatability validation.

Project State Update:
- State Version 66.
