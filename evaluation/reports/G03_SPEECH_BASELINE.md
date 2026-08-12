# G03 Speech Observation Baseline

Date: 2026-08-12
Status: Engineering baseline; not production quality admission

## Scope

- Provider: local FunASR-compatible service, adapter identity `funasr/openai-compatible-http/1.3.26`
- Execution: local CPU, legacy Narrato SRT transport
- Input: macOS Tingting synthetic Mandarin WAV, 70,362 bytes
- Reference: `我不答应他没有回来。`
- Rights: generated test speech; no drama asset used

## Result

| Metric | Result |
|---|---:|
| Adapter wall time | 1,313 ms |
| Timed segments | 1 |
| Speaker clusters | 1 (`speaker-1`) |
| Synthetic CER | 0.0 |
| Output range | 00:00:00.050–00:00:02.035 |
| Provider admission | research |

The result proves the local provider, legacy transport parser, typed normalization and
speaker-cluster boundary. It does not establish domain CER, entity CER, timestamp accuracy,
DER/JER, dialect/BGM/overlap quality, throughput, or a production threshold.

## Fail-closed qualification

The provider remains `research`: only the code license is known; the complete model-weight
checksum, exact model-card license, commercial approval, and real series-isolated benchmark
are missing. L1 and Confidence Shadow remain mandatory.
