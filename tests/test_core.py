"""Tests for the PDF operations. Run with `python3 test_ops.py` or `pytest`."""

import sys
from pathlib import Path

# Allow running this file directly (python tests/test_core.py) as well as
# under pytest; both need the repository root on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from pdftoolkit.core import pdf_ops as ops


def make_pdf(pages=5, text="Hello"):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 144), f"{text} {i + 1}", fontsize=30)
    data = doc.tobytes()
    doc.close()
    return data


def test_parse_pages():
    assert ops.parse_pages("1-3,5", 5) == [0, 1, 2, 4]
    assert ops.parse_pages("", 3) == [0, 1, 2]
    assert ops.parse_pages("2", 3) == [1]
    for bad in ["9", "abc", "3-1", "0"]:
        try:
            ops.parse_pages(bad, 5)
            raise AssertionError(f"{bad!r} should have been rejected")
        except ValueError:
            pass


def test_pdf_to_jpgs():
    pages = ops.pdf_to_jpgs(make_pdf(3), dpi=72)
    assert len(pages) == 3
    assert pages[0][0] == "page_001.jpg"
    assert all(data.startswith(b"\xff\xd8\xff") for _, data in pages)


def test_images_to_pdf():
    jpgs = ops.pdf_to_jpgs(make_pdf(2), dpi=72)
    assert ops.page_count(ops.images_to_pdf(jpgs)) == 2


def test_merge():
    merged = ops.merge_pdfs([("a.pdf", make_pdf(5)), ("b.pdf", make_pdf(2))])
    assert ops.page_count(merged) == 7


def test_split():
    parts = ops.split_to_pages(make_pdf(4))
    assert len(parts) == 4
    assert all(ops.page_count(data) == 1 for _, data in parts)


def test_extract_and_delete():
    pdf = make_pdf(5)
    assert ops.page_count(ops.extract_pages(pdf, "1-2,5")) == 3
    assert ops.page_count(ops.delete_pages(pdf, "2,4")) == 3
    try:
        ops.delete_pages(pdf, "1-5")
        raise AssertionError("deleting every page should fail")
    except ValueError:
        pass


def test_rotate():
    rotated = ops.rotate_pages(make_pdf(2), "1", 90)
    with fitz.open(stream=rotated, filetype="pdf") as doc:
        assert doc[0].rotation == 90
        assert doc[1].rotation == 0


def test_compress():
    pdf = make_pdf(3)
    assert len(ops.compress(pdf)) <= len(pdf)
    assert ops.page_count(ops.compress(pdf, rasterize=True, dpi=72)) == 3


def test_password():
    pdf = make_pdf(3)
    locked = ops.add_password(pdf, "secret123")
    try:
        ops.page_count(locked)
        raise AssertionError("locked PDF should need a password")
    except ValueError:
        pass
    assert ops.page_count(locked, "secret123") == 3
    with fitz.open(stream=ops.remove_password(locked, "secret123"), filetype="pdf") as doc:
        assert not doc.needs_pass


def test_extract_text():
    assert "Hello 1" in ops.extract_text(make_pdf(2))


def test_info():
    info = ops.pdf_info(make_pdf(3))
    assert info["Pages"] == 3
    assert info["Encrypted"] == "No"




def test_parse_order():
    assert ops.parse_order("3,1,1", 4) == [2, 0, 0]
    assert ops.parse_order("4-1", 4) == [3, 2, 1, 0]
    assert ops.parse_order("", 3) == [0, 1, 2]
    for bad in ["9", "abc"]:
        try:
            ops.parse_order(bad, 4)
            raise AssertionError(f"{bad!r} should have been rejected")
        except ValueError:
            pass


def test_hex_to_rgb():
    assert ops.hex_to_rgb("#000000") == (0.0, 0.0, 0.0)
    assert ops.hex_to_rgb("#ffffff") == (1.0, 1.0, 1.0)


def test_render_preview():
    assert ops.render_preview(make_pdf(3), 1, dpi=60).startswith(b"\xff\xd8\xff")


def test_add_text():
    out = ops.add_text(make_pdf(3), "1", "Approved", position="Top right", size=12)
    first_page = ops.extract_text(out).split("--- Page 2")[0]
    assert "Approved" in first_page
    try:
        ops.add_text(make_pdf(1), "", "   ")
        raise AssertionError("blank text should be rejected")
    except ValueError:
        pass


def test_add_image():
    stamp = ops.pdf_to_jpgs(make_pdf(1), dpi=50)[0][1]
    out = ops.add_image(make_pdf(2), "", stamp, width_pct=20, opacity=0.5)
    assert ops.page_count(out) == 2


def test_watermark():
    assert "DRAFT" in ops.extract_text(ops.add_watermark(make_pdf(2), "DRAFT"))


def test_page_numbers():
    text = ops.extract_text(
        ops.add_page_numbers(make_pdf(4), template="{n} / {total}", skip_first=True)
    )
    assert "2 / 4" in text and "1 / 4" not in text


def test_find_and_highlight():
    pdf = make_pdf(3, text="Secret")
    assert ops.find_text(pdf, "Secret") == [(1, 1), (2, 1), (3, 1)]
    _, hits = ops.highlight_text(pdf, "Secret")
    assert hits == 3
    try:
        ops.highlight_text(pdf, "nothing-here")
        raise AssertionError("missing phrase should be rejected")
    except ValueError:
        pass


def test_redact_removes_text():
    pdf = make_pdf(2, text="Secret")
    out, hits = ops.redact_text(pdf, "Secret")
    assert hits == 2
    assert "Secret" not in ops.extract_text(out)


def test_reorder():
    out = ops.reorder_pages(make_pdf(3), "3,2,1")
    assert "Hello 3" in ops.extract_text(out).split("--- Page 2")[0]


def test_page_spans_and_span_at():
    pdf = make_pdf(2)
    spans = ops.page_spans(pdf, 0)
    assert spans and "Hello 1" in spans[0]["text"]
    box = spans[0]["bbox"]
    mid = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    assert ops.span_at(pdf, 0, mid)["text"] == spans[0]["text"]
    assert ops.span_at(pdf, 0, (500, 750)) is None


def test_replace_span():
    pdf = make_pdf(2)
    span = ops.page_spans(pdf, 0)[0]
    out = ops.replace_span(pdf, 0, span["bbox"], "Goodbye world", span["size"], span["color"])
    first = ops.extract_text(out).split("--- Page 2")[0]
    assert "Goodbye world" in first and "Hello 1" not in first


def test_add_text_at():
    out = ops.add_text_at(make_pdf(1), 0, (200, 300), "Signed here", size=12)
    assert "Signed here" in ops.extract_text(out)


def test_render_page_px_scale():
    pdf = make_pdf(1)
    png, pt_per_px = ops.render_page_px(pdf, 0, width_px=600)
    width_pt, _ = ops.page_size(pdf)
    assert png.startswith(b"\x89PNG")
    assert abs(600 * pt_per_px - width_pt) < 1


def test_remove_restrictions():
    doc = fitz.open()
    doc.new_page().insert_text((72, 120), "Restricted", fontsize=20)
    restricted = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,
                             owner_pw="owner", user_pw="",
                             permissions=int(fitz.PDF_PERM_ACCESSIBILITY))
    doc.close()
    out = ops.remove_restrictions(restricted)
    with fitz.open(stream=out, filetype="pdf") as freed:
        assert not freed.needs_pass
        assert "Restricted" in freed[0].get_text()

    # a PDF that needs a password just to open must be refused, not faked
    locked = ops.add_password(make_pdf(1), "secret")
    try:
        ops.remove_restrictions(locked)
        raise AssertionError("should refuse a user-password PDF")
    except ValueError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} tests passed")
