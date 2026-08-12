import React, { useEffect, useMemo, useState } from "react";

import type { TimelineReviewPackage } from "./generated/contracts.generated";
import { buildTimelineReviewView } from "./timelineReview";

type ReviewSnapshot = {
  review_id: string;
  project_id: string;
  state: string;
  target_version: number;
  package: TimelineReviewPackage;
};

type Decision = "approve" | "reject" | "revise";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function shortRef(ref: { artifact_type: string; artifact_id: string; version: number }): string {
  return `${ref.artifact_type} · ${ref.artifact_id.slice(0, 8)} · v${ref.version}`;
}

export function TimelineWorkspace({ reviewId }: { reviewId: string }): React.JSX.Element {
  const [snapshot, setSnapshot] = useState<ReviewSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [actorId, setActorId] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/v1/reviews/timeline/${reviewId}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`加载审核任务失败 (${response.status})`);
        return response.json() as Promise<ReviewSnapshot>;
      })
      .then(setSnapshot)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "加载失败");
      });
    return () => controller.abort();
  }, [reviewId]);

  const view = useMemo(
    () => (snapshot ? buildTimelineReviewView(snapshot.package) : null),
    [snapshot],
  );

  async function decide(decision: Decision): Promise<void> {
    if (!snapshot || !view || busy || !actorId.trim()) return;
    if (decision === "approve" && !view.approvalEnabled) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/v1/reviews/${snapshot.review_id}/decision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Actor-Id": actorId.trim(),
          "X-Actor-Roles": "reviewer",
          "X-Actor-Type": "human",
        },
        body: JSON.stringify({
          expected_target_version: snapshot.target_version,
          decision,
          reasons: note.trim() ? [{ kind: "editor_note", text: note.trim() }] : [],
        }),
      });
      if (!response.ok) throw new Error(`提交决定失败 (${response.status})`);
      setSnapshot({ ...snapshot, state: "decided" });
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "提交失败");
    } finally {
      setBusy(false);
    }
  }

  if (error && !snapshot) return <main className="center-state"><h1>无法打开审核任务</h1><p>{error}</p></main>;
  if (!snapshot || !view) return <main className="center-state"><p>正在加载 Timeline checkpoint…</p></main>;

  const refs = [
    snapshot.package.master_timeline_ref,
    snapshot.package.preview_ref,
    snapshot.package.creative_brief_ref,
    snapshot.package.approved_story_ref,
  ];
  const decided = snapshot.state !== "awaiting_review";
  return (
    <main className="workspace">
      <header className="workspace-header">
        <div><p className="eyebrow">E09 · TIMELINE CHECKPOINT</p><h1>剪辑意图审核台</h1></div>
        <span className={`status ${decided ? "closed" : "open"}`}>{snapshot.state}</span>
      </header>

      <section className="preview-panel" aria-label="完整预览">
        <div className="preview-placeholder"><span>Preview Artifact</span><strong>{shortRef(snapshot.package.preview_ref)}</strong><p>播放器接入真实代理媒体后才允许全片画面审核。</p></div>
        <aside><h2>精确引用</h2>{refs.map((ref) => <code key={`${ref.artifact_id}:${ref.version}`}>{shortRef(ref)}</code>)}</aside>
      </section>

      <section className="timeline-panel">
        <div className="section-title"><div><p className="eyebrow">SINGLE SOURCE OF TIME</p><h2>多轨时间线</h2></div><span>v{snapshot.target_version}</span></div>
        <div className="tracks">{view.tracks.map((track, index) => <div className="track" key={track}><b>{track.replaceAll("_", " ")}</b><div className={`track-lane lane-${index}`}><span>Exact-ref track data pending media projection</span></div></div>)}</div>
      </section>

      <section className="review-grid">
        <article><h2>阻断与风险</h2>{view.approvalDisabledReasons.length ? <ul>{view.approvalDisabledReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <p className="pass">未发现 Contract 阻断项</p>}</article>
        <article><h2>审核意见</h2><label className="field-label">审核人 ID<input value={actorId} onChange={(event) => setActorId(event.target.value)} placeholder="输入当前人工审核人标识" disabled={decided} /></label><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="记录需要修改的时间码、原因和预期结果" disabled={decided} /></article>
      </section>

      {error ? <p className="inline-error">{error}</p> : null}
      <footer className="actions"><button disabled={decided || busy || !actorId.trim()} onClick={() => void decide("reject")}>拒绝</button><button disabled={decided || busy || !actorId.trim()} onClick={() => void decide("revise")}>退回修改</button><button className="primary" disabled={decided || busy || !actorId.trim() || !view.approvalEnabled} onClick={() => void decide("approve")}>批准 Timeline Intent</button></footer>
    </main>
  );
}
