"""Command line: convert each page of a PDF into a JPG image."""

import sys
from pathlib import Path

from ops import pdf_to_jpgs


def pdf_to_jpg(pdf_path, out_dir=None):
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir) if out_dir else pdf_path.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = pdf_to_jpgs(pdf_path.read_bytes())
    for name, data in pages:
        (out_dir / name).write_bytes(data)
        print(f"saved {out_dir / name}")
    print(f"\n{len(pages)} pages -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python main.py <file.pdf> [output_dir]")
    pdf_to_jpg(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
