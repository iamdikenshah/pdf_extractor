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
  html, body { margin: 0; height: 100%; }
  #boot {
    position: fixed; inset: 0; z-index: 9999;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 1.1rem; background: #F6F7FB; color: #1B1F35;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    transition: opacity .4s ease;
  }
  #boot.done { opacity: 0; pointer-events: none; }
  .badge {
    width: 62px; height: 62px; border-radius: 18px;
    background: linear-gradient(135deg, #4F46E5 0%, #7C6BF5 100%);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 10px 30px rgba(79,70,229,.35);
  }
  .title { font-size: 1.35rem; font-weight: 700; letter-spacing: -.02em; }
  .sub { color: #6B7192; font-size: .92rem; max-width: 30rem; text-align: center;
         line-height: 1.55; padding: 0 1.5rem; }
  .bar { width: 210px; height: 5px; border-radius: 999px; background: #E5E7F0; overflow: hidden; }
  .bar span {
    display: block; width: 40%; height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #4F46E5, #7C6BF5);
    animation: slide 1.25s ease-in-out infinite;
  }
  @keyframes slide { 0% { transform: translateX(-110%); } 100% { transform: translateX(360%); } }
  .note { color: #8A90AC; font-size: .78rem; }
</style>
</head>
<body>
<div id="boot">
  <div class="badge">
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="white"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/>
    </svg>
  </div>
  <div class="title">PDF Toolkit</div>
  <div class="bar"><span></span></div>
  <div class="sub">Setting up. The first visit downloads the PDF engine, then it is
    cached and opens straight away.</div>
  <div class="note">Your files never leave this device.</div>
</div>

<div id="root"></div>

<script type="module">
import * as stlite from "https://cdn.jsdelivr.net/npm/@stlite/browser@__STLITE__/build/stlite.js";

stlite.mount(__CONFIG__, document.getElementById("root"));

// hide the splash once Streamlit has painted
const boot = document.getElementById("boot");
const watcher = new MutationObserver(() => {
  if (document.querySelector('[data-testid="stAppViewContainer"]')) {
    boot.classList.add("done");
    setTimeout(() => boot.remove(), 500);
    watcher.disconnect();
  }
});
watcher.observe(document.body, { childList: true, subtree: true });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
