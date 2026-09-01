"""D5 pre-annotation: machine-prefill the annotation worksheet with research
providers (PaddleOCR / RT-DETR / Ark VLM) on the 24 kit frames.

The prefill is a convenience: every field is marked ``machine_prefill`` and the
project owner still owns the final annotation (``ocr_reference_text`` /
``det_reference_boxes`` / ``vlm_claim_verdict`` stay empty for the owner to
fill or correct). Machine output is research and fail-closed — no value is
treated as ground truth.
"""

# ruff: noqa: RUF001 - CJK prompt/claims are intentional.

from __future__ import annotations

import json
from pathlib import Path

from packages.contracts import ArtifactRef, ProviderCapability, ProviderInvocationRequest
from packages.providers.visual.paddle_detection import PaddleDetectionProvider
from packages.providers.visual.paddle_ocr import PaddleOCRProvider
from packages.providers.visual.volcengine_ark_vlm import VolcengineArkVLMProvider

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "evaluation/evidence/d5_annotation_kit"
FRAMES = KIT / "frames"
WORKSHEET = KIT / "annotation_worksheet.json"
DUMMY = ArtifactRef.model_validate(
    {
        "artifact_id": "6f0e9d2a-3b4c-4d5e-8f9a-0b1c2d3e4f50",
        "version": 1,
        "artifact_type": "ConfigArtifact",
    }
)
VLM_PROMPT = "用一句话描述画面：人物、场景、关键物体或文本；若含剧情元素请指出。只输出描述。"


def _request(
    frame: Path, capability: ProviderCapability, prompt: str | None = None
) -> ProviderInvocationRequest:
    params: dict[str, object] = {"frame_path": str(frame)}
    if prompt:
        params["prompt"] = prompt
    return ProviderInvocationRequest(
        capability=capability,
        inputs=(DUMMY,),
        config_ref=DUMMY,
        resource_profile_ref=DUMMY,
        idempotency_key=f"d5-prefill:{frame.stem}",
        timeout_ms=120_000,
        parameters=params,
    )


def _parse_ocr(payload: bytes) -> list[dict[str, object]]:
    raw = json.loads(payload)
    items = []
    for item in raw.get("ocr", []) or raw.get("results", []) or []:
        if isinstance(item, dict) and item.get("text"):
            items.append({"text": item["text"], "score": item.get("score")})
    return items


def _parse_det(payload: bytes) -> list[dict[str, object]]:
    raw = json.loads(payload)
    items = []
    for item in raw.get("detections", []) or raw.get("objects", []) or []:
        if isinstance(item, dict):
            items.append({"label": item.get("label"), "score": item.get("score")})
    return items


def _parse_vlm(payload: bytes) -> str:
    raw = json.loads(payload)
    claims = raw.get("vlm_claims") or []
    return str(claims[0].get("statement") or "") if claims else ""


def main() -> int:
    ocr = PaddleOCRProvider()
    det = PaddleDetectionProvider()
    vlm = VolcengineArkVLMProvider()
    worksheet = json.loads(WORKSHEET.read_text(encoding="utf-8"))
    rows = worksheet["frames"]
    for row in rows:
        frame = FRAMES / row["frame"]
        if not frame.is_file():
            print(f"skip missing {row['frame']}")
            continue
        try:
            ocr_items = _parse_ocr(ocr.infer(_request(frame, ProviderCapability.OCR)).payload)
        except Exception as exc:
            ocr_items = []
            print(f"  OCR failed {row['frame']}: {exc}")
        try:
            det_items = _parse_det(det.infer(_request(frame, ProviderCapability.DETECTION)).payload)
        except Exception as exc:
            det_items = []
            print(f"  DET failed {row['frame']}: {exc}")
        try:
            vlm_text = _parse_vlm(
                vlm.infer(_request(frame, ProviderCapability.VLM, VLM_PROMPT)).payload
            )
        except Exception as exc:
            vlm_text = ""
            print(f"  VLM failed {row['frame']}: {exc}")
        row["machine_prefill"] = {
            "ocr_detected_texts": ocr_items,
            "detection_objects": det_items,
            "vlm_description": vlm_text,
            "note": "machine research prefill; owner must verify/correct before use as reference",
        }
        print(
            f"{row['frame']}: OCR={len(ocr_items)} DET={len(det_items)} "
            f"VLM={'ok' if vlm_text else 'fail'}"
        )
    worksheet["instructions"]["machine_prefill_note"] = (
        "以下 machine_prefill 为 research 机器输出，仅供提示，不作为参考标准；"
        "请以画面实际内容为准填写/修正三栏标注。"
    )
    WORKSHEET.write_text(json.dumps(worksheet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"== prefill done: {WORKSHEET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
