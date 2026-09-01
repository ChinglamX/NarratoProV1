# E10 Voice, Audio and Subtitle Runbook

1. Consume only exact Approved Timeline Intent and approved profiles.
2. Admit TTS only with code/model/voice rights, checksum, pronunciation benchmark and rollback provider.
3. Bound takes and cost per line; unavailable never masquerades as silence or success.
4. Select only committed audio with measured duration; align tokens/lines and conform Timeline successor.
5. Limit reflow to affected Beat/neighbors; invalidate subtitle/mix/render exact dependency closure.
6. Require RightsMetadata for original audio, voice, BGM, SFX, font and graphics.
7. BGM requires explicit ducking; measure output against versioned loudness/True Peak profile.
8. Build subtitles from alignment, reject overlap/out-of-text highlights, then check visual safe area.
9. Render ASS with fixed libass/font profile and compare preview/final geometry.
10. Any rights, sync, intelligibility, masking or safe-area blocker stops E11 preflight.
11. Time-base discipline (E09 ADR-051 lesson): alignment tokens and conform cues are computed via `seconds` semantics and must not mix rational rates. `duration_delta` requires identical rates; `build_subtitle_cues` derives cue ranges from token seconds, so microsecond-based alignment is safe but rate mixing is rejected. Do not reintroduce rate-1 cursor accumulation when extending conform.
