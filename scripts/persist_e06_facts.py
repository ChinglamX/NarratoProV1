"""Persist E06-derived OCR Facts into PostgreSQL as FactSet artifacts.

Reads the enriched visual benchmark, rebuilds VisualObservation + fusion per
episode (fuse_observations) and commits each FactSet through ArtifactRepository.
This puts the OCR->Fact evidence chain into the system data store for Story
consumption. Research evidence; not an admission decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import uuid4

from packages.contracts import ActorRef, ArtifactRef, ProviderIdentity
from packages.foundation.settings import get_settings
from packages.intelligence.facts import fuse_observations
from packages.intelligence.visual import normalize_visual_response
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine

BENCHMARK = "evaluation/benchmarks/e06_visual_v1_enriched.json"


def _ref(kind: str, artifact_id=None) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(artifact_id or uuid4()), "version": 1, "artifact_type": kind}
    )


def _fuse_episode(series_id: str, episode: dict[str, object], provider: ProviderIdentity) -> object:
    caps = episode["capabilities"]
    ocr_items = [
        item
        for r in caps["ocr"]["results"]
        if "ocr" in r
        for item in r["ocr"]
        if str(item.get("text", "")).strip() and item.get("region")
    ]
    det_items = [
        item
        for r in caps["detection"]["results"]
        if "detections" in r
        for item in r["detections"]
        if item.get("region")
    ]
    if not ocr_items and not det_items:
        return None
    raw = {
        "frames": [
            {
                "frame": {
                    "frame_ref": _ref("SourceMedia").model_dump(mode="json"),
                    "sample_id": str(uuid4()),
                    "source_time": {"value": 0, "rate_num": 25},
                },
                "ocr": [
                    {"text": i["text"], "region": i["region"], "kind": i.get("kind", "unknown")}
                    for i in ocr_items[:8]
                ],
                "detections": [
                    {"label": i.get("label", "unknown"), "region": i["region"]}
                    for i in det_items[:8]
                ],
            }
        ]
    }
    source_ref = _ref("SourceMedia")
    visual_ref = _ref("VisualObservation")
    observation = normalize_visual_response(
        raw,
        source_ref=source_ref,
        frame_plan_ref=_ref("CreativeBrief"),
        raw_response_refs=(visual_ref,),
        provider=provider,
    )
    report = fuse_observations(
        fact_set_ref=_ref("FactSet"),
        visual_ref=visual_ref,
        visual=observation,
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-series", help="subset for dev")
    args = parser.parse_args()

    with open(BENCHMARK, encoding="utf-8") as handle:
        benchmark = json.loads(handle.read())
    engine = create_database_engine(get_settings().database_url)
    with engine.connect() as connection:
        project_id = connection.execute(
            __import__("sqlalchemy").text("select id from core.project limit 1")
        ).scalar()
    run_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            __import__("sqlalchemy").text(
                "insert into core.run (id, project_id, workflow_id, state, "
                "automation_policy_snapshot, resource_profile_snapshot) "
                "values (:i,:p,:w,'running','{}','{}')"
            ),
            {"i": run_id, "p": project_id, "w": f"e07-facts/{run_id}"},
        )
    actor = ActorRef.model_validate({"kind": "human", "id": "e06-facts-persist"})
    provider = ProviderIdentity.model_validate(
        {
            "provider": "e06-benchmark",
            "version": "v1",
            "implementation": "paddle+ark",
            "license": "Apache-2.0",
        }
    )
    rp_ref = _ref("ResourceProfile")
    committed = total_facts = 0
    with engine.begin() as connection:
        for series_id, series in benchmark["series"].items():
            if args.limit_series and series_id not in args.limit_series.split(","):
                continue
            for ep_id, episode in series["episodes"].items():
                report = _fuse_episode(series_id, episode, provider)
                if report is None:
                    continue
                commit_contract_artifact(
                    connection,
                    ArtifactRepository(),
                    artifact_id=uuid4(),
                    artifact_type="FactSet",
                    payload=report.fact_set,
                    project_id=project_id,
                    run_id=run_id,
                    variant_id=None,
                    trace_id="e" * 32,
                    actor=actor,
                    producer_module="e07-facts-persist",
                    module_version="v1",
                    resource_profile_ref=rp_ref,
                    rights_class="internal-observation",
                    inputs=(),
                )
                committed += 1
                total_facts += len(report.fact_set.facts)
                print(f"  {series_id[:20]} {ep_id}: FactSet ({len(report.fact_set.facts)} facts)")
    print(f"committed {committed} FactSet artifacts, {total_facts} facts, run={run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
