"""Convert each page of a PDF into a JPG image."""

import sys
from pathlib import Path

import fitz  # PyMuPDF

DPI = 200
QUALITY = 90


def pdf_to_jpg_bytes(pdf_bytes, dpi=DPI, quality=QUALITY):
    """Yield (filename, jpg_bytes) for each page of an in-memory PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        yield f"page_{i:03d}.jpg", pix.tobytes("jpg", jpg_quality=quality)
    doc.close()


def pdf_to_jpg(pdf_path, out_dir=None):
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir) if out_dir else pdf_path.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for name, data in pdf_to_jpg_bytes(pdf_path.read_bytes()):
        (out_dir / name).write_bytes(data)
        print(f"saved {out_dir / name}")
        count += 1
    print(f"\n{count} pages -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python main.py <file.pdf> [output_dir]")
    pdf_to_jpg(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
