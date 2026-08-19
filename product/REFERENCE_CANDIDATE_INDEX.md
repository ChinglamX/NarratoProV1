# Reference Candidate Index

Version: 1.0  
Updated: 2026-08-19

Large media stays outside Git. This index is the lightweight recovery proof for the current director-assisted regression and held-out anchor validation.

## Candidate v3 — Director-assisted regression

- Mode: `director_assisted_reference`
- Config: `product/series_main_cut_v3.json`
- Config SHA-256: `1a0437ada022dc7c2cad7057c00e419216f0b66d95051e08ab0e4bb90f8a9281`
- Manifest: `outputs/series_main_cut/candidate_v3/manifest.json`
- Manifest SHA-256: `50b9e3d5da552c10431c3871e47829576961611bbccd515dada20e7d3e5f608e`
- Video: `outputs/series_main_cut/candidate_v3/candidate_v3.mp4`
- Video SHA-256: `4d48b4fdfa54c1870b61bbbdb05f52b5452af8540d56da11ddecd92a22075e22`
- Human evidence: narration continuity accepted; audiovisual match assessed as basically matched.
- Boundary: not automatic story/clip/narration generation proof; no Release Gate 3.

## Episodes 7–8 — Held-out anchor validation

- Mode: `tool_scheduled_from_director_events`
- Config: `product/heldout_episode_7_8_anchor_validation.json`
- Config SHA-256: `0064e29700032bb7844f81f12d96d013aef9ee33dfd81bd65cd8f778bbe83327`
- Manifest: `outputs/heldout_episode_7_8/candidate_v1/manifest.json`
- Manifest SHA-256: `f068b917077a2d8b8ce11bfb0f2927fc7bfac42ebee0565096a67ae658193581`
- Video: `outputs/heldout_episode_7_8/candidate_v1/candidate_v1.mp4`
- Video SHA-256: `77b5d770d6f2123f5fbb7e35f4ed6850dee7923ce4f84fa54d572c39340cf2c2`
- Timing: seven narration lines scheduled from evidence events after measured TTS; zero absolute director-authored cue starts; zero manual timing overrides; zero blocking anchor findings.
- Technical: 40.00s, 720x1280 H.264/AAC, mean -20.3 dB, max -2.9 dB.
- Human evidence: product owner decision=`useful` on 2026-08-19.
- Boundary: Anchor scheduling reaches M3 Human Useful; no canonical held-out E10/E11 and no Release Gate 3.
