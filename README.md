# PDF Toolkit

A local PDF workbench with a Streamlit web UI. Files are processed on your own
machine -- nothing is uploaded anywhere.

## Tools

| Tool | What it does |
|---|---|
| PDF to JPG | Render every page as a JPG, download singly or as a ZIP |
| Images to PDF | Combine JPG/PNG/BMP/GIF/TIFF/WEBP into one PDF, one image per page |
| Extract text | Pull out the text and download it as `.txt` |
| **Edit PDF** | Page-by-page editor: rewrite the text already in the PDF, or click to add new text |
| Apply to all pages | Watermarks, page numbers, stamps, find-and-highlight, find-and-redact, reorder |
| Merge PDFs | Join several PDFs in the order you upload them |
| Split PDF | Break a PDF into one file per page |
| Extract pages | Keep only the pages you choose (`1-3, 5, 8-10`) |
| Delete pages | Remove the pages you choose |
| Rotate pages | Turn selected pages 90/180/270 degrees |
| Compress PDF | Lossless cleanup, or aggressive rasterising for much smaller files |
| Protect / Unlock | Add an AES-256 password, or remove a known one |
| PDF info | Page count, size, author, encryption status |

Password protected PDFs are handled throughout -- a password box appears when
one is needed.

### About Edit PDF

A full width editor that works one page at a time:

- **Edit text** -- click a line of text on the page (or pick it from the list) and
  rewrite it. The old glyphs are removed and the new text is written in their place.
- **Add text** -- type it, then click the page where it should start.

Each page is a draft until you keep it. Press **Next** with unsaved changes and the
editor asks whether to keep them or throw them away before it moves on. **Undo**
steps back one change, **Revert page** drops all of them, **Save this page** commits.
The download always matches what you see on screen.

Two honest limits:

- The replacement text is set in Helvetica at the original size. A PDF's embedded
  fonts are usually subsets that hold only the glyphs already used, so they cannot
  render new characters.
- Scanned pages contain images, not text, so there is nothing to rewrite. The
  editor says so rather than failing quietly.

Rewriting a whole paragraph with reflow is not offered, because a PDF stores
positioned glyphs rather than editable paragraphs.

## Two ways to run it

**On your own machine** -- the quick start below.

**As a website** -- `python3 build_web.py` regenerates `index.html` at the root of
the repository. That single file runs the whole app in the visitor's browser
through [stlite](https://github.com/whitphx/stlite), which is Streamlit compiled
to WebAssembly. Python and PyMuPDF are downloaded once by the browser and every
conversion runs on the visitor's own machine, so:

- no PDF is ever uploaded to a server, which keeps the privacy notice honest
- there is no upload or download wait, and no file size limit beyond their RAM
- speed depends on their computer, not on a shared server
- hosting is free and static: GitHub Pages, Netlify, any web host

The cost is a one-off download of about 40 MB on the first visit (roughly ten
seconds on a fast connection), cached from then on.

GitHub Pages serves `index.html` from the repository root in its default
"deploy from a branch" mode, so pushing to `main` publishes it. The `.nojekyll`
file matters: without it Pages hands the repository to Jekyll, which publishes
`README.md` as the home page instead of the app.

Run `python3 build_web.py` and commit the result whenever you change the app,
otherwise the published page keeps the previous version.

## Quick start

Double-click **`run.command`** in Finder. It installs anything missing, starts
the server, and opens the app in your browser. Closing the Terminal window stops it.

From a terminal, `./run.sh` does the same thing.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Uploads up to 300 MB are accepted, set in `.streamlit/config.toml`.

## Command line

The PDF-to-JPG conversion is also a CLI:

```bash
python main.py file.pdf            # writes to ./file/
python main.py file.pdf ./images   # or a directory you choose
```

## Architecture

The code is a layered package. The rule is simple: **`core` never imports from
`ui`, and `ui` never contains PDF or image logic.** That keeps the operations
usable from the web UI, the CLI and the tests without dragging Streamlit along.

```
pdf_extractor/
├── app.py                    # Streamlit entrypoint (thin composition root)
├── main.py                   # command-line entrypoint
├── build_web.py              # bundles the package into index.html (stlite/WASM)
├── index.html                # generated static site -- rebuild, don't edit
├── pdftoolkit/
│   ├── core/                 # pure logic, no UI, no Streamlit
│   │   ├── pdf_ops.py        #   every PDF operation, functions on bytes
│   │   └── image_ops.py      #   every image operation, functions on bytes
│   ├── ui/                   # Streamlit presentation only
│   │   ├── registry.py       #   the tools: metadata + menu grouping (one source)
│   │   ├── theme.py          #   setup, sidebar, page chrome, CSS loader
│   │   ├── helpers.py        #   shared widgets (upload, run button, downloads)
│   │   ├── editor.py         #   the page editor (currently hidden)
│   │   └── pages/            #   one module per tool group; each exports PAGES
│   │       ├── convert.py    #     {name: render_fn} entries the app collects
│   │       ├── images.py
│   │       ├── organise.py
│   │       ├── optimise.py
│   │       ├── secure.py
│   │       ├── info.py
│   │       └── apply_all.py  #     the batch editor (currently hidden)
│   └── assets/styles.css     # the light theme
└── tests/test_core.py        # tests for pdftoolkit.core
```

**How a tool is wired.** `registry.py` lists each tool's icon, description and
which group it sits in -- that alone controls the menu. Each `pages/*.py` module
maps display names to render functions in a `PAGES` dict; `pages/__init__.py`
merges them, and `app.py` matches the two by name. Adding a tool means writing a
render function, adding it to its group module's `PAGES`, and adding one line to
`registry.py`.

**Two runtimes.** `app.py` runs under Streamlit locally, and `build_web.py`
bundles the whole package into `index.html` to run in the browser via stlite
(Pyodide/WASM). The build discovers every file under `pdftoolkit/`, so a new
module is included automatically -- but you must re-run `python3 build_web.py`
and commit `index.html` for the hosted site to pick up a change.

Run the tests with `pytest` (config in `pyproject.toml`) or `python3
tests/test_core.py`. Defaults (`DPI = 200`, `QUALITY = 90`) live at the top of
`pdftoolkit/core/pdf_ops.py`; theme colours are in `.streamlit/config.toml` and
`pdftoolkit/assets/styles.css`.
