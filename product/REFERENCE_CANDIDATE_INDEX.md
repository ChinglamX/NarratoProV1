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
- Config SHA-256: `6623fce4d6dd0154f0bb61d2c5cd14c22df24eeb826b20d340647c768331a367`
- Canonical ingest episode 7: `outputs/heldout_episode_7_8/ingest_episode_07.json` (`58ebf2e040f96484cc529f5f3929df202742c654f14cf17107323bd10872a1e1`)
- Canonical ingest episode 8: `outputs/heldout_episode_7_8/ingest_episode_08.json` (`c25081abfcf4a6d4a3efd4a1e997b16a9282a03a3ea91c81577caf8fc741453c`)
- Manifest: `outputs/heldout_episode_7_8/candidate_v1/manifest.json`
- Manifest SHA-256: `f068b917077a2d8b8ce11bfb0f2927fc7bfac42ebee0565096a67ae658193581`
- Video: `outputs/heldout_episode_7_8/candidate_v1/candidate_v1.mp4`
- Video SHA-256: `77b5d770d6f2123f5fbb7e35f4ed6850dee7923ce4f84fa54d572c39340cf2c2`
- Canonical acceptance: `outputs/heldout_episode_7_8/candidate_v1/canonical_acceptance.json` (`e195eb28d192c14d506c32297e9c6452f54cc977eed8135377ae4dcc4a0168e4`)
- Canonical video: `outputs/heldout_episode_7_8/candidate_v1/canonical_e11.mp4` (`e84c5d18bc4c180b95a93fbf46bca7ca39d120b6ec184e1837fa22b07eb68e5d`)
- Timing: seven narration lines scheduled from evidence events after measured TTS; zero absolute director-authored cue starts; zero manual timing overrides; zero blocking anchor findings.
- Technical: 40.00s, 720x1280 H.264/AAC, mean -20.3 dB, max -2.9 dB.
- Human evidence: product owner decision=`useful` on 2026-08-19.
- Canonical: two independent runs passed Temporal Technical QC with no blocked codes and produced the identical canonical video checksum.
- Boundary: Anchor scheduling reaches M3 Human Useful and this held-out production slice reaches M4 Slice Integrated; no automatic upstream generation proof and no Release Gate 3.
