"""PDF operations. Pure functions on bytes -- no UI code here."""

import fitz  # PyMuPDF

DPI = 200
QUALITY = 90


def _open(pdf_bytes, password=None):
    """Open a PDF, unlocking it first if it is password protected."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.needs_pass and not doc.authenticate(password or ""):
        doc.close()
        raise ValueError("This PDF is password protected. Enter the correct password.")
    return doc


def page_count(pdf_bytes, password=None):
    with _open(pdf_bytes, password) as doc:
        return doc.page_count


def parse_pages(spec, total):
    """Turn a page spec like '1-3,5' into zero-based indices. Empty means all pages."""
    spec = (spec or "").strip()
    if not spec:
        return list(range(total))

    pages = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                start_text, _, end_text = part.partition("-")
                start, end = int(start_text), int(end_text)
            else:
                start = end = int(part)
        except ValueError:
            raise ValueError(f"'{part}' is not a page number or range.") from None
        if start < 1 or end > total or start > end:
            raise ValueError(f"'{part}' is out of range for a {total}-page PDF.")
        pages.extend(range(start - 1, end))

    if not pages:
        raise ValueError("No pages selected.")
    return sorted(set(pages))


def pdf_to_jpgs(pdf_bytes, dpi=DPI, quality=QUALITY, password=None):
    """One JPG per page. Returns [(filename, jpg_bytes), ...]."""
    with _open(pdf_bytes, password) as doc:
        return [
            (f"page_{i:03d}.jpg", page.get_pixmap(dpi=dpi).tobytes("jpg", jpg_quality=quality))
            for i, page in enumerate(doc, start=1)
        ]


def images_to_pdf(images):
    """Build a PDF from [(filename, image_bytes), ...], one image per page."""
    if not images:
        raise ValueError("No images given.")

    out = fitz.open()
    for name, data in images:
        ext = name.rsplit(".", 1)[-1].lower()
        with fitz.open(stream=data, filetype=ext) as img:
            rect = img[0].rect
            pdf_bytes = img.convert_to_pdf()
        with fitz.open("pdf", pdf_bytes) as page_pdf:
            out.new_page(width=rect.width, height=rect.height).show_pdf_page(rect, page_pdf, 0)

    data = out.tobytes(garbage=4, deflate=True)
    out.close()
    return data


def merge_pdfs(pdfs):
    """Join [(filename, pdf_bytes), ...] into one PDF, in the order given."""
    if not pdfs:
        raise ValueError("No PDFs given.")

    out = fitz.open()
    for name, data in pdfs:
        try:
            with _open(data) as doc:
                out.insert_pdf(doc)
        except ValueError:
            out.close()
            raise ValueError(f"'{name}' is password protected -- unlock it first.") from None

    data = out.tobytes(garbage=4, deflate=True)
    out.close()
    return data


def split_to_pages(pdf_bytes, password=None):
    """One single-page PDF per page. Returns [(filename, pdf_bytes), ...]."""
    with _open(pdf_bytes, password) as doc:
        results = []
        for i in range(doc.page_count):
            single = fitz.open()
            single.insert_pdf(doc, from_page=i, to_page=i)
            results.append((f"page_{i + 1:03d}.pdf", single.tobytes(garbage=4, deflate=True)))
            single.close()
        return results


def extract_pages(pdf_bytes, spec, password=None):
    """A new PDF holding only the selected pages."""
    with _open(pdf_bytes, password) as doc:
        pages = parse_pages(spec, doc.page_count)
        out = fitz.open()
        for i in pages:
            out.insert_pdf(doc, from_page=i, to_page=i)
        data = out.tobytes(garbage=4, deflate=True)
        out.close()
        return data


def delete_pages(pdf_bytes, spec, password=None):
    """A new PDF with the selected pages removed."""
    with _open(pdf_bytes, password) as doc:
        drop = set(parse_pages(spec, doc.page_count))
        keep = [i for i in range(doc.page_count) if i not in drop]
        if not keep:
            raise ValueError("That would delete every page.")
        doc.delete_pages(sorted(drop))
        return doc.tobytes(garbage=4, deflate=True)


def rotate_pages(pdf_bytes, spec, angle, password=None):
    """Rotate the selected pages by 90, 180 or 270 degrees."""
    if angle % 90:
        raise ValueError("Rotation must be a multiple of 90 degrees.")
    with _open(pdf_bytes, password) as doc:
        for i in parse_pages(spec, doc.page_count):
            page = doc[i]
            page.set_rotation((page.rotation + angle) % 360)
        return doc.tobytes(garbage=4, deflate=True)


def compress(pdf_bytes, password=None, rasterize=False, dpi=150, quality=70):
    """Shrink a PDF. Rasterizing compresses far more but turns text into images."""
    with _open(pdf_bytes, password) as doc:
        if not rasterize:
            return doc.tobytes(garbage=4, deflate=True, clean=True)

        out = fitz.open()
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            with fitz.open(stream=pix.tobytes("jpg", jpg_quality=quality), filetype="jpg") as img:
                pdf_page = img.convert_to_pdf()
            with fitz.open("pdf", pdf_page) as page_pdf:
                out.new_page(width=page.rect.width, height=page.rect.height).show_pdf_page(
                    page.rect, page_pdf, 0
                )
        data = out.tobytes(garbage=4, deflate=True)
        out.close()
        return data


def add_password(pdf_bytes, new_password, password=None):
    """Encrypt with AES-256."""
    if not new_password:
        raise ValueError("Enter a password to set.")
    with _open(pdf_bytes, password) as doc:
        return doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=new_password,
            user_pw=new_password,
            garbage=4,
            deflate=True,
        )


def remove_password(pdf_bytes, password):
    """Strip encryption, given the current password."""
    with _open(pdf_bytes, password) as doc:
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True)


def extract_text(pdf_bytes, password=None):
    """Plain text of the whole document, with a header per page."""
    with _open(pdf_bytes, password) as doc:
        return "\n\n".join(
            f"--- Page {i} ---\n{page.get_text().strip()}" for i, page in enumerate(doc, start=1)
        )


def pdf_info(pdf_bytes, password=None):
    """Basic metadata for display."""
    with _open(pdf_bytes, password) as doc:
        meta = doc.metadata or {}
        first = doc[0].rect if doc.page_count else None
        return {
            "Pages": doc.page_count,
            "Title": meta.get("title") or "-",
            "Author": meta.get("author") or "-",
            "Producer": meta.get("producer") or "-",
            "Created": meta.get("creationDate") or "-",
            "Encrypted": "Yes" if doc.needs_pass else "No",
            "First page size": f"{first.width:.0f} x {first.height:.0f} pt" if first else "-",
        }
