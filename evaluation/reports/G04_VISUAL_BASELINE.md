# G04 Visual Observation Baseline

Date: 2026-08-12
Status: Engineering baseline; not production quality admission

## Implemented boundary

- Typed OCR/TextTrack, Detection, Shot-local Tracklet, Face/Appearance, VisualEmbedding,
  constrained VLM claim, quality and bounded supplementary-sampling contracts.
- Provider-agnostic typed JSON HTTP adapter for OCR/detection/tracking/face/embedding/VLM.
- OpenCV 5.0.0.93 local contour/quality research adapter.
- Source-frame/time evidence, Shadow Confidence, explicit unavailable, resource batch admission,
  Temporal Activity and immutable raw→normalized Artifact lineage.

## Real frame engineering result

Input: ignored local demo extraction `demo_frames/frame_0001.jpg`; no asset copied into Git.

| Metric | Result |
|---|---:|
| Adapter wall time | 24 ms |
| Foreground candidates | 8 |
| Mean luminance | 0.3148 |
| Contrast | 0.3669 |
| Laplacian blur score | 48.4065 |
| Identity usability rule | false |
| Provider admission | research |

Contours are generic foreground regions, not person identity or semantic detections. This run proves
decode, accounting, source evidence and quality-feature transport only.

## Provider qualification status

- PaddleOCR 3.x/PP-OCRv5: candidate; no pinned local runtime/model checksum or benchmark installed.
- Ultralytics YOLO: blocked from production unless project license posture is explicitly compatible
  with AGPL or an Enterprise license is approved.
- Grounding DINO/ByteTrack/OpenCLIP/SigLIP/Qwen-VL: candidates only; exact code revision, each
  checkpoint license/checksum, hardware profile and real series-isolated benchmark remain required.

Therefore OCR, semantic detection, tracking quality, identity candidate quality, embedding retrieval
and VLM correctness have no production thresholds. L1/Shadow and unavailable/manual fallback remain
mandatory.
