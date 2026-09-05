# PDF to JPG

Convert every page of a PDF into a JPG image — via a Streamlit web UI or the command line.

## Setup

```bash
pip install -r requirements.txt
```

## Web UI

```bash
streamlit run app.py
```

Upload a PDF, adjust DPI and quality if needed, then press **Convert**. Download the
pages individually or all at once as a ZIP. Uploads up to 300 MB are accepted
(configured in `.streamlit/config.toml`).

## Command line

```bash
python main.py file.pdf            # writes to ./file/
python main.py file.pdf ./images   # or a directory you choose
```

Pages are saved as `page_001.jpg`, `page_002.jpg`, ... so they sort correctly.

## Settings

Defaults live at the top of `main.py`:

- `DPI = 200` — raise to 300 for print quality, lower for smaller files
- `QUALITY = 90` — JPEG quality, 50-100
