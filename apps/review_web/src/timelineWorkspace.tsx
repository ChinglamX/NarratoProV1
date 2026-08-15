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

type TimelineChangeDto = {
  item_id: string;
  change: string;
  before_version: number | null;
  after_version: number | null;
};

type VersionSummaryDto = {
  version: number;
  producer: Record<string, unknown>;
  changes: TimelineChangeDto[];
};

type PartialPreviewDto = {
  timeline_id: string;
  from_version: number;
  to_version: number;
  output_path: string;
  subtitle_path: string;
  original_start: number;
  original_end: number;
  duration_seconds: number;
};

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
  const [versions, setVersions] = useState<VersionSummaryDto[] | null>(null);
  const [versionsError, setVersionsError] = useState<string | null>(null);
  const [fromVersion, setFromVersion] = useState<number | "">("");
  const [toVersion, setToVersion] = useState<number | "">("");
  const [diff, setDiff] = useState<TimelineChangeDto[] | null>(null);
  const [partial, setPartial] = useState<PartialPreviewDto | null>(null);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

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

  const timelineId = snapshot?.package.master_timeline_ref.artifact_id ?? null;

  useEffect(() => {
    if (!timelineId) return;
    const controller = new AbortController();
    setVersionsError(null);
    fetch(`${API_BASE}/v1/timelines/${timelineId}/versions?limit=50`, {
      signal: controller.signal,
      headers: { "X-Actor-Roles": "reviewer,editor" },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`加载版本历史失败 (${response.status})`);
        return response.json() as Promise<{ versions: VersionSummaryDto[] }>;
      })
      .then((body) => setVersions(body.versions))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setVersionsError(reason instanceof Error ? reason.message : "版本加载失败");
        }
      });
    return () => controller.abort();
  }, [timelineId]);

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

  async function loadDiff(): Promise<void> {
    if (!timelineId || fromVersion === "" || toVersion === "") return;
    setEditBusy(true);
    setEditError(null);
    setDiff(null);
    try {
      const response = await fetch(
        `${API_BASE}/v1/timelines/${timelineId}/diff?from_version=${fromVersion}&to_version=${toVersion}`,
        { headers: { "X-Actor-Roles": "reviewer,editor" } },
      );
      if (!response.ok) throw new Error(`diff 失败 (${response.status})`);
      const body = (await response.json()) as { changes: TimelineChangeDto[] };
      setDiff(body.changes);
    } catch (reason: unknown) {
      setEditError(reason instanceof Error ? reason.message : "diff 失败");
    } finally {
      setEditBusy(false);
    }
  }

  async function renderPartial(): Promise<void> {
    if (!timelineId || fromVersion === "" || toVersion === "") return;
    setEditBusy(true);
    setEditError(null);
    setPartial(null);
    try {
      const response = await fetch(`${API_BASE}/v1/timelines/${timelineId}/preview-partial`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Actor-Roles": "reviewer,editor" },
        body: JSON.stringify({ from_version: fromVersion, to_version: toVersion }),
      });
      if (!response.ok) {
        const detail = (await response.json().catch(() => null)) as { detail?: { message?: string } } | null;
        throw new Error(detail?.detail?.message ?? `局部预览失败 (${response.status})`);
      }
      setPartial((await response.json()) as PartialPreviewDto);
    } catch (reason: unknown) {
      setEditError(reason instanceof Error ? reason.message : "局部预览失败");
    } finally {
      setEditBusy(false);
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
  const versionOptions = versions?.map((v) => v.version) ?? [];
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

      <section className="timeline-panel" aria-label="版本历史与编辑预览">
        <div className="section-title"><div><p className="eyebrow">APPEND-ONLY VERSIONS</p><h2>版本与局部预览</h2></div><span>{versions ? `${versions.length} 个版本` : "加载中…"}</span></div>
        {versionsError ? <p className="inline-error">{versionsError}</p> : null}
        <div className="version-list">
          {(versions ?? []).map((v) => (
            <div className="version-row" key={v.version}>
              <strong>v{v.version}</strong>
              <span>{String(v.producer?.kind ?? "timeline")}</span>
              <span className="change-tags">{(v.changes ?? []).slice(0, 3).map((c) => <code key={`${v.version}:${c.item_id}:${c.change}`}>{c.change}</code>)}</span>
            </div>
          ))}
        </div>
        <div className="diff-tools">
          <label className="field-label">From 版本
            <select value={fromVersion} onChange={(event) => setFromVersion(event.target.value === "" ? "" : Number(event.target.value))}>
              <option value="">选择…</option>
              {versionOptions.map((v) => <option key={`from-${v}`} value={v}>v{v}</option>)}
            </select>
          </label>
          <label className="field-label">To 版本
            <select value={toVersion} onChange={(event) => setToVersion(event.target.value === "" ? "" : Number(event.target.value))}>
              <option value="">选择…</option>
              {versionOptions.map((v) => <option key={`to-${v}`} value={v}>v{v}</option>)}
            </select>
          </label>
          <button disabled={editBusy || fromVersion === "" || toVersion === ""} onClick={() => void loadDiff()}>查看 Diff</button>
          <button className="primary" disabled={editBusy || fromVersion === "" || toVersion === ""} onClick={() => void renderPartial()}>渲染局部预览</button>
        </div>
        {editError ? <p className="inline-error">{editError}</p> : null}
        {diff !== null ? (
          <div className="diff-result">
            <h3>Diff 结果（{diff.length} 项）</h3>
            {diff.length === 0 ? <p>无差异</p> : <ul>{diff.map((c) => <li key={`${c.item_id}:${c.change}`}><code>{c.change}</code> {c.item_id.slice(0, 8)} <span className="muted">before={c.before_version ?? "—"} after={c.after_version ?? "—"}</span></li>)}</ul>}
          </div>
        ) : null}
        {partial !== null ? (
          <div className="diff-result">
            <h3>局部预览已渲染</h3>
            <ul>
              <li>区间：{partial.original_start.toFixed(2)}s → {partial.original_end.toFixed(2)}s（时长 {partial.duration_seconds.toFixed(2)}s）</li>
              <li>视频：<code>{partial.output_path}</code></li>
              <li>字幕：<code>{partial.subtitle_path}</code></li>
            </ul>
            <p className="muted">服务器端渲染完成；可打开本地文件或经静态服务器播放。</p>
          </div>
        ) : null}
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
