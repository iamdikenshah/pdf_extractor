"""Build web/index.html: the whole app as a static page that runs in the browser.

Uses stlite, which is Streamlit compiled to WebAssembly. Python and PyMuPDF are
downloaded once by the visitor's browser and everything runs on their machine,
so no PDF is ever uploaded anywhere.

    python3 build_web.py    ->  index.html
"""

import json
import tomllib
from pathlib import Path

STLITE = "1.8.1"
APP_FILES = ["app.py", "ops.py", "ui.py", "editor.py", "styles.css"]
REQUIREMENTS = ["pymupdf", "pillow", "streamlit-image-coordinates"]

HERE = Path(__file__).parent
# The page lives at the repo root because that is what GitHub Pages serves in
# its default "deploy from a branch" mode. Without a root index.html, Pages
# hands the site to Jekyll, which publishes README.md as the home page instead.
OUT = HERE / "index.html"


def streamlit_config():
    """Reuse the local theme so the hosted page looks the same."""
    config = tomllib.loads((HERE / ".streamlit" / "config.toml").read_text())
    flat = {f"{section}.{key}": value
            for section, values in config.items()
            for key, value in values.items()}
    flat["client.toolbarMode"] = "minimal"
    return flat


def build():
    files = {name: (HERE / name).read_text() for name in APP_FILES}
    payload = json.dumps(
        {"entrypoint": "app.py", "requirements": REQUIREMENTS,
         "files": files, "streamlitConfig": streamlit_config()},
        indent=2,
    )

    OUT.write_text(TEMPLATE.replace("__CONFIG__", payload).replace("__STLITE__", STLITE))
    (HERE / ".nojekyll").touch()  # stop Jekyll rewriting the page

    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB) with {len(files)} app files")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>PDF Toolkit</title>
<meta name="description" content="Edit, convert and organise PDFs. Runs entirely in your browser." />
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#128196;</text></svg>" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@__STLITE__/build/stlite.css" />
<style>
  html, body { margin: 0; height: 100%; background: #F6F7FB; }

  #boot {
    position: fixed; inset: 0; z-index: 9999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 1rem; background: #F6F7FB; color: #1B1F35;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    transition: opacity .45s ease;
  }
  #boot.done { opacity: 0; pointer-events: none; }

  .badge {
    width: 60px; height: 60px; border-radius: 18px;
    background: linear-gradient(135deg, #4F46E5 0%, #7C6BF5 100%);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 10px 30px rgba(79,70,229,.32);
  }

  .title { font-size: 1.3rem; font-weight: 700; letter-spacing: -.02em; }

  .bar {
    width: 230px; height: 6px; border-radius: 999px;
    background: #E5E7F0; overflow: hidden;
  }
  .bar > i {
    display: block; height: 100%; width: 0%; border-radius: 999px;
    background: linear-gradient(90deg, #4F46E5, #7C6BF5);
    transition: width .6s cubic-bezier(.4,0,.2,1);
  }

  .stage { font-size: .88rem; color: #4B5170; min-height: 1.2em; font-weight: 550; }
  .note {
    color: #8A90AC; font-size: .78rem; text-align: center;
    max-width: 24rem; padding: 0 1.5rem; line-height: 1.5;
  }
  .note.hidden { visibility: hidden; }

  @media (prefers-reduced-motion: reduce) {
    .bar > i { transition: none; }
    #boot { transition: none; }
  }
</style>
</head>
<body>
<div id="boot" role="status" aria-live="polite">
  <div class="badge">
    <svg width="29" height="29" viewBox="0 0 24 24" fill="none" stroke="white"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/>
    </svg>
  </div>
  <div class="title">PDF Toolkit</div>
  <div class="bar"><i id="boot-bar"></i></div>
  <div class="stage" id="boot-stage">Starting</div>
  <div class="note" id="boot-note">Setting up the PDF engine. This happens on your first
    visit only, then it is cached and opens straight away.</div>
</div>

<div id="root"></div>

<script type="module">
import * as stlite from "https://cdn.jsdelivr.net/npm/@stlite/browser@__STLITE__/build/stlite.js";

const boot  = document.getElementById("boot");
const bar   = document.getElementById("boot-bar");
const stage = document.getElementById("boot-stage");
const note  = document.getElementById("boot-note");

// A repeat visitor has the engine cached, so do not promise them a long wait.
let returning = false;
try { returning = localStorage.getItem("pdf-toolkit-loaded") === "1"; } catch (e) {}
if (returning) note.classList.add("hidden");

// stlite reports its progress as plain text. Map what it says onto the bar, so
// the movement reflects real work rather than a timer.
const STAGES = [
  ["Loading Pyodide",  18, "Starting the engine"],
  ["Mounting files",   34, "Loading the app"],
  ["Unpacking",        48, "Unpacking"],
  ["Mocking",          58, "Preparing"],
  ["Installing",       72, "Fetching the PDF engine"],
];

let pct = 6;
const setBar = (value, label) => {
  pct = Math.max(pct, value);           // never go backwards
  bar.style.width = pct + "%";
  if (label) stage.textContent = label;
};
setBar(6, returning ? "Starting" : "Downloading");

const ready = () => document.querySelector('#root [data-testid="stSidebar"]');

// Poll on a timer rather than observing mutations. stlite churns the DOM hard
// while it boots, and reacting to every mutation (especially by reading
// innerText, which forces a layout) is enough to freeze the page. textContent
// costs nothing and 400ms is plenty for a progress label.
const poll = setInterval(() => {
  if (ready()) {
    clearInterval(poll);
    setBar(100, "Ready");
    boot.classList.add("done");
    try { localStorage.setItem("pdf-toolkit-loaded", "1"); } catch (e) {}
    setTimeout(() => boot.remove(), 500);
    return;
  }
  const said = document.getElementById("root")?.textContent || "";
  for (const [needle, value, label] of STAGES) {
    if (said.includes(needle)) setBar(value, label);
  }
  if (pct >= 72 && pct < 93) setBar(pct + 1);   // gentle creep on the long stage
}, 400);

// If it never arrives, say so rather than spinning forever.
setTimeout(() => {
  if (!ready()) {
    stage.textContent = "Still working";
    note.classList.remove("hidden");
    note.textContent = "This is taking longer than usual. A slow connection can do it. " +
                       "Reloading the page is safe and picks up whatever has cached.";
  }
}, 60000);

stlite.mount(__CONFIG__, document.getElementById("root"));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
