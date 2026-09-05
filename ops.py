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


# --- editing ---------------------------------------------------------------

POSITIONS = [
    "Top left", "Top centre", "Top right",
    "Middle left", "Centre", "Middle right",
    "Bottom left", "Bottom centre", "Bottom right",
]

NUMBER_FORMATS = {"1": "{n}", "Page 1": "Page {n}", "1 / 10": "{n} / {total}"}


def hex_to_rgb(value):
    """'#4F46E5' -> (0.31, 0.27, 0.90)."""
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def parse_order(spec, total):
    """Like parse_pages but keeps your order and allows repeats: '3,1,1' -> [2,0,0]."""
    spec = (spec or "").strip()
    if not spec:
        return list(range(total))

    order = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a, _, b = part.partition("-")
                start, end = int(a), int(b)
                step = 1 if end >= start else -1
                chunk = list(range(start, end + step, step))
            else:
                chunk = [int(part)]
        except ValueError:
            raise ValueError(f"'{part}' is not a page number or range.") from None
        for n in chunk:
            if not 1 <= n <= total:
                raise ValueError(f"Page {n} does not exist in a {total}-page PDF.")
            order.append(n - 1)

    if not order:
        raise ValueError("No pages selected.")
    return order


def _place(page_rect, position, width, height, margin):
    """Top-left corner for a `width` x `height` box placed at `position`."""
    row, _, col = position.lower().partition(" ")
    x = {"left": margin,
         "centre": (page_rect.width - width) / 2,
         "right": page_rect.width - width - margin}[col]
    y = {"top": margin,
         "middle": (page_rect.height - height) / 2,
         "bottom": page_rect.height - height - margin}[row]
    return x, y


def render_preview(pdf_bytes, index=0, dpi=90, password=None):
    """One page as a JPG, for on-screen previews."""
    with _open(pdf_bytes, password) as doc:
        index = max(0, min(index, doc.page_count - 1))
        return doc[index].get_pixmap(dpi=dpi).tobytes("jpg", jpg_quality=85)


def add_text(pdf_bytes, spec, text, position="Bottom centre", size=14, color="#1B1F35",
             opacity=1.0, margin=36, password=None):
    """Stamp a line (or several) of text onto the selected pages."""
    if not text.strip():
        raise ValueError("Enter the text you want to add.")

    lines = text.splitlines() or [text]
    font = fitz.Font("helv")
    rgb = hex_to_rgb(color)
    leading = size * 1.35

    with _open(pdf_bytes, password) as doc:
        for i in parse_pages(spec, doc.page_count):
            page = doc[i]
            block_w = max(font.text_length(line, size) for line in lines)
            block_h = leading * len(lines)
            x, y = _place(page.rect, position, block_w, block_h, margin)
            writer = fitz.TextWriter(page.rect)
            for row, line in enumerate(lines):
                if line.strip():
                    writer.append(fitz.Point(x, y + size + row * leading), line,
                                  font=font, fontsize=size)
            writer.write_text(page, color=rgb, opacity=opacity)
        return doc.tobytes(garbage=4, deflate=True)


def add_image(pdf_bytes, spec, image_bytes, position="Bottom right", width_pct=25,
              opacity=1.0, margin=36, password=None):
    """Place an image (logo, signature, stamp) on the selected pages."""
    pix = fitz.Pixmap(image_bytes)
    if opacity < 1:
        if not pix.alpha:
            pix = fitz.Pixmap(pix, 1)
        pix.set_alpha(bytes([int(255 * opacity)]) * (pix.width * pix.height))
    image_bytes = pix.tobytes("png")
    ratio = pix.height / pix.width

    with _open(pdf_bytes, password) as doc:
        for i in parse_pages(spec, doc.page_count):
            page = doc[i]
            width = page.rect.width * width_pct / 100
            height = width * ratio
            x, y = _place(page.rect, position, width, height, margin)
            page.insert_image(fitz.Rect(x, y, x + width, y + height),
                              stream=image_bytes, overlay=True)
        return doc.tobytes(garbage=4, deflate=True)


def add_watermark(pdf_bytes, text, spec="", size=60, color="#9AA0BD", opacity=0.25,
                  angle=45, password=None):
    """Diagonal watermark across the selected pages."""
    if not text.strip():
        raise ValueError("Enter the watermark text.")

    font = fitz.Font("helv")
    rgb = hex_to_rgb(color)

    with _open(pdf_bytes, password) as doc:
        for i in parse_pages(spec, doc.page_count):
            page = doc[i]
            width = font.text_length(text, size)
            centre = fitz.Point(page.rect.width / 2, page.rect.height / 2)
            writer = fitz.TextWriter(page.rect)
            writer.append(fitz.Point(centre.x - width / 2, centre.y + size / 3), text,
                          font=font, fontsize=size)
            writer.write_text(page, color=rgb, opacity=opacity,
                              morph=(centre, fitz.Matrix(angle)))
        return doc.tobytes(garbage=4, deflate=True)


def add_page_numbers(pdf_bytes, position="Bottom centre", start=1, template="{n}",
                     size=10, color="#6B7192", margin=28, skip_first=False, password=None):
    """Number the pages."""
    font = fitz.Font("helv")
    rgb = hex_to_rgb(color)

    with _open(pdf_bytes, password) as doc:
        total = doc.page_count
        for i, page in enumerate(doc):
            if skip_first and i == 0:
                continue
            label = template.format(n=i + start, total=total + start - 1)
            width = font.text_length(label, size)
            x, y = _place(page.rect, position, width, size, margin)
            writer = fitz.TextWriter(page.rect)
            writer.append(fitz.Point(x, y + size), label, font=font, fontsize=size)
            writer.write_text(page, color=rgb)
        return doc.tobytes(garbage=4, deflate=True)


def find_text(pdf_bytes, query, password=None):
    """Where a phrase appears: [(page number, hits), ...]."""
    if not query.strip():
        raise ValueError("Enter the text to search for.")
    with _open(pdf_bytes, password) as doc:
        return [(i + 1, len(page.search_for(query))) for i, page in enumerate(doc)
                if page.search_for(query)]


def highlight_text(pdf_bytes, query, color="#FFE066", password=None):
    """Highlight every occurrence. Returns (pdf_bytes, hit count)."""
    if not query.strip():
        raise ValueError("Enter the text to highlight.")
    rgb = hex_to_rgb(color)

    with _open(pdf_bytes, password) as doc:
        hits = 0
        for page in doc:
            for rect in page.search_for(query):
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=rgb)
                annot.update()
                hits += 1
        if not hits:
            raise ValueError(f"'{query}' was not found in this PDF.")
        return doc.tobytes(garbage=4, deflate=True), hits


def redact_text(pdf_bytes, query, fill="#000000", password=None):
    """Permanently remove every occurrence. Returns (pdf_bytes, hit count)."""
    if not query.strip():
        raise ValueError("Enter the text to redact.")
    rgb = hex_to_rgb(fill)

    with _open(pdf_bytes, password) as doc:
        hits = 0
        for page in doc:
            for rect in page.search_for(query):
                page.add_redact_annot(rect, fill=rgb)
                hits += 1
            if hits:
                page.apply_redactions()
        if not hits:
            raise ValueError(f"'{query}' was not found in this PDF.")
        return doc.tobytes(garbage=4, deflate=True), hits


def reorder_pages(pdf_bytes, spec, password=None):
    """Rebuild the document in the given page order."""
    with _open(pdf_bytes, password) as doc:
        doc.select(parse_order(spec, doc.page_count))
        return doc.tobytes(garbage=4, deflate=True)


# --- page level editing ----------------------------------------------------
#
# Everything below works on a single page and takes coordinates in PDF points,
# so the editor can translate a click on a rendered image straight into a change.


def page_size(pdf_bytes, index=0, password=None):
    with _open(pdf_bytes, password) as doc:
        rect = doc[index].rect
        return rect.width, rect.height


def render_page_px(pdf_bytes, index=0, width_px=760, password=None):
    """Render a page to a PNG about `width_px` wide.

    Returns (png_bytes, points_per_pixel) so a click on the image can be
    converted back into PDF coordinates.
    """
    with _open(pdf_bytes, password) as doc:
        page = doc[max(0, min(index, doc.page_count - 1))]
        zoom = width_px / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png"), 1 / zoom


def _int_to_rgb(value):
    return ((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255


def page_spans(pdf_bytes, index=0, password=None):
    """Every run of text on the page, with its box, size and colour."""
    with _open(pdf_bytes, password) as doc:
        spans = []
        for block in doc[index].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].strip():
                        spans.append({
                            "text": span["text"],
                            "bbox": tuple(span["bbox"]),
                            "size": span["size"],
                            "font": span["font"],
                            "color": _int_to_rgb(span["color"]),
                            "origin": tuple(span["origin"]),
                        })
        return spans


def span_at(pdf_bytes, index, point, password=None):
    """The text run under a point, if any. Picks the smallest box that contains it."""
    x, y = point
    hits = [s for s in page_spans(pdf_bytes, index, password)
            if s["bbox"][0] <= x <= s["bbox"][2] and s["bbox"][1] <= y <= s["bbox"][3]]
    if not hits:
        return None
    return min(hits, key=lambda s: (s["bbox"][2] - s["bbox"][0]) * (s["bbox"][3] - s["bbox"][1]))


def replace_span(pdf_bytes, index, bbox, new_text, size=None, color=None, password=None):
    """Replace one run of text: remove the old glyphs, write the new ones in place.

    The original font is not always embeddable, so the replacement is set in
    Helvetica at the same size and colour.
    """
    with _open(pdf_bytes, password) as doc:
        page = doc[index]
        rect = fitz.Rect(bbox)
        page.add_redact_annot(rect)
        try:
            page.apply_redactions(images=0, graphics=0)
        except TypeError:  # older PyMuPDF
            page.apply_redactions()

        if new_text.strip():
            font = fitz.Font("helv")
            size = size or max(6, rect.height * 0.82)
            # shrink to fit if the new text is longer than the space it replaces
            while size > 4 and font.text_length(new_text, size) > rect.width * 1.6:
                size -= 0.5
            writer = fitz.TextWriter(page.rect)
            writer.append(fitz.Point(rect.x0, rect.y1 - rect.height * 0.18), new_text,
                          font=font, fontsize=size)
            writer.write_text(page, color=color or (0, 0, 0))
        return doc.tobytes(garbage=4, deflate=True)


def add_text_at(pdf_bytes, index, point, text, size=14, color="#1B1F35",
                opacity=1.0, password=None):
    """Write text with its top-left corner at `point`."""
    if not text.strip():
        raise ValueError("Enter some text first.")
    font = fitz.Font("helv")
    with _open(pdf_bytes, password) as doc:
        page = doc[index]
        writer = fitz.TextWriter(page.rect)
        for row, line in enumerate(text.splitlines() or [text]):
            if line.strip():
                writer.append(fitz.Point(point[0], point[1] + size * (row + 1)), line,
                              font=font, fontsize=size)
        writer.write_text(page, color=hex_to_rgb(color), opacity=opacity)
        return doc.tobytes(garbage=4, deflate=True)
