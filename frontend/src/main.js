import "./app.css";
import App from "./App.svelte";

function showGlobalError(message) {
  const box = document.createElement("div");
  box.style.position = "fixed";
  box.style.bottom = "12px";
  box.style.right = "12px";
  box.style.background = "#ef4444";
  box.style.color = "#fff";
  box.style.padding = "12px 14px";
  box.style.borderRadius = "10px";
  box.style.fontFamily = "monospace";
  box.style.zIndex = "9999";
  box.textContent = message;
  document.body.appendChild(box);
}

window.addEventListener("error", (e) => {
  showGlobalError(e.message || "Unknown error");
});
window.addEventListener("unhandledrejection", (e) => {
  const msg = (e.reason && e.reason.message) || String(e.reason) || "Unhandled rejection";
  showGlobalError(msg);
});

let app;
try {
  // Use `new App` to stay aligned with Svelte 5 compatibility mode.
  app = new App({
    target: document.getElementById("app"),
  });
  if (window.__appBootTimer) {
    clearTimeout(window.__appBootTimer);
  }
} catch (err) {
  const target = document.getElementById("app");
  if (target) {
    target.innerHTML =
      "<div style='color:#e6edf3;padding:24px;font-family:Manrope,system-ui,sans-serif'>App failed to load: " +
      (err?.message || err) +
      "</div>";
  }
  showGlobalError(err?.message || "App failed to start");
}

export default app;
