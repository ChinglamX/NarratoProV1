"""D5 annotation metrics runner.

Reads the owner-filled annotation worksheet (evaluation/evidence/d5_annotation_kit/
annotation_worksheet.json) and computes per-frame and per-episode metrics:

- OCR: character error rate between the owner's reference text and the machine
  OCR prefill (only for frames where the owner supplied a reference).
- DET: label-presence precision/recall between the owner's box description
  (labels mentioned) and the machine detection labels. NOTE: the trial sheet
  asks for a text description, so this is a label-level proxy, not IoU mAP;
  precise mAP needs explicit reference boxes (a D5 extension).
- VLM: evidence compliance = fraction of machine VLM descriptions the owner
  marked related and not hallucinated.

Empty owner fields are skipped and reported, so the script can run before and
during annotation. Output: evaluation/evidence/d5_annotation_kit/metrics_report.json
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from packages.evaluation.visual_metrics import ocr_character_error_rate

_CJK_PUNCT = "、，。！？；：（）《》「」【】()"  # noqa: RUF001 - punctuation set is intentional


def _normalize_ocr_text(value: str) -> str:
    """Strip whitespace and CJK/half-width punctuation for a punctuation/
    space-insensitive trial OCR CER (documented; exact CER can re-introduce
    punctuation later)."""
    return "".join(ch for ch in value if ch not in _CJK_PUNCT and not ch.isspace())


# Known fixed watermarks on the s07 (AI-generated) series, including the
# truncation variants observed in machine output.
_WATERMARK_PATTERN = re.compile(
    r"剧情纯属虚构请勿模仿|剧情纯属虚构|纯衣构请勿模仿|衣构请勿模仿|情纯|"
    r"内容由AI生成|内容由A生成|容由A生成|由AI生成|由A生成|又子劇場|子劇場|剧場|剧情"
)


def strip_watermarks(value: str) -> str:
    """Remove known fixed-watermark substrings (and observed truncations)."""
    return _WATERMARK_PATTERN.sub("", value)


ROOT = Path(__file__).resolve().parents[1]
WORKSHEET = ROOT / "evaluation/evidence/d5_annotation_kit/annotation_worksheet.json"
OUTPUT = ROOT / "evaluation/evidence/d5_annotation_kit/metrics_report.json"

# Machine detection labels that carry meaning for short-drama scenes, plus the
# common Chinese tokens the owner naturally writes in the worksheet. Matching
# normalizes Chinese tokens to their English label.
LABEL_NORMALIZE = {
    "人": "person",
    "people": "person",
    "卡": "card",
    "车": "vehicle",
    "car": "vehicle",
    "钱": "money",
    "手机": "phone",
}


def parse_owner_labels(description: str) -> set[str]:
    """Extract normalized labels mentioned in the owner's box description."""
    lowered = (description or "").lower()
    found = set()
    for token, normalized in LABEL_NORMALIZE.items():
        if token in lowered:
            found.add(normalized)
    # also accept the English label itself
    if "person" in lowered or "people" in lowered:
        found.add("person")
    return found


def main() -> int:
    worksheet = json.loads(WORKSHEET.read_text(encoding="utf-8"))
    rows = [row for row in worksheet["frames"] if row.get("annotated_by") == "project-owner"]
    per_episode: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "ocr_total": 0,
            "cer_sum": 0.0,
            "det_tp": 0,
            "det_fp": 0,
            "det_fn": 0,
            "vlm_checked": 0,
            "vlm_ok": 0,
            "ocr_false_positive": 0,
            "dialogue_ocr_total": 0,
            "dialogue_cer_sum": 0.0,
        }
    )
    skipped = 0
    for row in rows:
        ep = f"{row['series']}/{row['episode']}"
        stats = per_episode[ep]
        prefill = row.get("machine_prefill", {})
        owner_ocr = (row.get("ocr_reference_text") or "").strip()
        machine_text = "".join(item["text"] for item in prefill.get("ocr_detected_texts", []))
        dialogue_ref = (row.get("dialogue_text") or "").strip()
        if dialogue_ref:
            stats["dialogue_ocr_total"] += 1
            stats["dialogue_cer_sum"] += ocr_character_error_rate(
                _normalize_ocr_text(dialogue_ref),
                _normalize_ocr_text(strip_watermarks(machine_text)),
            )
        if owner_ocr:
            stats["ocr_total"] += 1
            stats["cer_sum"] += ocr_character_error_rate(
                _normalize_ocr_text(owner_ocr), _normalize_ocr_text(machine_text)
            )
        elif machine_text:
            # Empty reference but machine emitted text: a false positive.
            # CER with an empty reference is undefined; count the frame as
            # 100% error and track it separately.
            stats["ocr_total"] += 1
            stats["cer_sum"] += 1.0
            stats["ocr_false_positive"] += 1
        owner_det = (row.get("det_reference_boxes") or "").strip()
        if owner_det:
            reference_labels = set(parse_owner_labels(owner_det))
            machine_labels = {
                LABEL_NORMALIZE.get(raw, raw)
                for item in prefill.get("detection_objects", [])
                if (raw := str(item.get("label") or "").lower())
            }
            for label in reference_labels:
                if label in machine_labels:
                    stats["det_tp"] += 1
                else:
                    stats["det_fn"] += 1
            stats["det_fp"] += sum(1 for label in machine_labels if label not in reference_labels)
        owner_vlm = (row.get("vlm_claim_verdict") or "").strip()
        if owner_vlm:
            stats["vlm_checked"] += 1
            hallucinated = owner_vlm.split("hallucinated")[-1]
            stats["vlm_ok"] += int("related" in owner_vlm and "yes" not in hallucinated)
        if not (owner_ocr or owner_det or owner_vlm):
            skipped += 1

    episodes = []
    for ep, stats in sorted(per_episode.items()):
        det_refs = stats["det_tp"] + stats["det_fn"]
        det_hyp = stats["det_tp"] + stats["det_fp"]
        episodes.append(
            {
                "episode": ep,
                "ocr_frames_annotated": stats["ocr_total"],
                "ocr_false_positive_frames": stats["ocr_false_positive"],
                "dialogue_only_cer": (
                    round(stats["dialogue_cer_sum"] / stats["dialogue_ocr_total"], 4)
                    if stats["dialogue_ocr_total"]
                    else None
                ),
                "ocr_mean_cer": (
                    round(stats["cer_sum"] / stats["ocr_total"], 4) if stats["ocr_total"] else None
                ),
                "det_label_precision": round(stats["det_tp"] / det_hyp, 4) if det_hyp else None,
                "det_label_recall": round(stats["det_tp"] / det_refs, 4) if det_refs else None,
                "vlm_frames_checked": stats["vlm_checked"],
                "vlm_compliance": (
                    round(stats["vlm_ok"] / stats["vlm_checked"], 4)
                    if stats["vlm_checked"]
                    else None
                ),
            }
        )
    report = {
        "scope": "D5 trial metrics (owner-annotated worksheet); label-level DET proxy, "
        "not IoU mAP; CER and claim compliance as defined in visual_metrics.py",
        "frames_total": len(rows),
        "frames_with_any_annotation": len(rows) - skipped,
        "frames_skipped": skipped,
        "notes": [
            "OCR CER is punctuation/space-insensitive (CJK punctuation and whitespace normalized).",
            "Empty-reference frames where the machine emitted text count as "
            "false positives and contribute 1.0 to mean CER.",
            "DET is label-level proxy (presence), not IoU mAP.",
        ],
        "episodes": episodes,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if skipped == len(rows):
        print("NOTE: no owner annotations yet; annotate the worksheet then re-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
