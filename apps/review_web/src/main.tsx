import React from "react";
import { createRoot } from "react-dom/client";
import { TimelineWorkspace } from "./timelineWorkspace";
import "./styles.css";

function App(): React.JSX.Element {
  const reviewId = new URLSearchParams(window.location.search).get("review_id");
  if (!reviewId) {
    return <main className="center-state"><h1>NarratoPro Review Workspace</h1><p>使用 <code>?review_id=&lt;uuid&gt;</code> 打开 Timeline checkpoint。</p></main>;
  }
  return <TimelineWorkspace reviewId={reviewId} />;
}

createRoot(document.getElementById("root")!).render(<App />);
