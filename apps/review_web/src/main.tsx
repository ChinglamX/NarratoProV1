import React from "react";
import { createRoot } from "react-dom/client";

function App(): React.JSX.Element {
  return <main><h1>NarratoPro Review Workspace</h1><p>Bootstrap shell</p></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
