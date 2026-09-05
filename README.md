# PDF Toolkit

A local PDF workbench with a Streamlit web UI. Files are processed on your own
machine -- nothing is uploaded anywhere.

## Tools

| Tool | What it does |
|---|---|
| PDF to JPG | Render every page as a JPG, download singly or as a ZIP |
| Images to PDF | Combine JPG/PNG/BMP/GIF/TIFF/WEBP into one PDF, one image per page |
| Extract text | Pull out the text and download it as `.txt` |
| **Edit PDF** | Add text, images and signatures, watermarks, page numbers; highlight, redact and reorder -- with a live preview and undo |
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

Editing works as a session: upload once, apply as many changes as you like,
watch each one land in the live preview, undo anything, then download the
result. Available changes:

- **Add text** -- any position, size, colour and opacity, on chosen pages
- **Add image or signature** -- PNG with transparency works best
- **Watermark** -- diagonal, adjustable angle and opacity
- **Page numbers** -- `1`, `Page 1` or `1 / 10`, optionally skipping the cover
- **Highlight** -- every occurrence of a phrase
- **Redact** -- permanently deletes the text from the file, not just covers it
- **Reorder pages** -- give a new order such as `3,1,2`

Note that rewriting a PDF's *existing* body text is not something this (or any)
tool can do reliably: a PDF stores positioned glyphs rather than editable
paragraphs. Everything above works by layering onto the page, which is how PDF
editors handle it.

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

## Layout

- `ops.py` -- every PDF operation, as plain functions on bytes. No UI code.
- `app.py` -- the Streamlit interface.
- `ui.py` -- theme, icons and page chrome.
- `styles.css` -- the light theme.
- `main.py` -- the command line entry point.
- `test_ops.py` -- tests. Run `python3 test_ops.py` or `pytest`.

Defaults (`DPI = 200`, `QUALITY = 90`) live at the top of `ops.py`. Theme
colours are in `.streamlit/config.toml` and `styles.css`.
