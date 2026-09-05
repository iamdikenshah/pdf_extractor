# PDF Toolkit

A local PDF workbench with a Streamlit web UI. Files are processed on your own
machine -- nothing is uploaded anywhere.

## Tools

| Tool | What it does |
|---|---|
| PDF to JPG | Render every page as a JPG, download singly or as a ZIP |
| Images to PDF | Combine JPG/PNG/BMP/GIF/TIFF/WEBP into one PDF, one image per page |
| Merge PDFs | Join several PDFs in the order you upload them |
| Split PDF | Break a PDF into one file per page |
| Extract pages | Keep only the pages you choose (`1-3, 5, 8-10`) |
| Delete pages | Remove the pages you choose |
| Rotate pages | Turn selected pages 90/180/270 degrees |
| Compress PDF | Lossless cleanup, or aggressive rasterizing for much smaller files |
| Protect / Unlock | Add an AES-256 password, or remove a known one |
| Extract text | Pull out the text and download it as `.txt` |
| PDF info | Page count, size, author, encryption status |

Password protected PDFs are handled throughout -- a password box appears when
one is needed.

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
- `main.py` -- the command line entry point.
- `test_ops.py` -- tests. Run `python3 test_ops.py` or `pytest`.

Defaults (`DPI = 200`, `QUALITY = 90`) live at the top of `ops.py`.
