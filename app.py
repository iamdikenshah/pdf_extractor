"""Streamlit UI for the PDF toolkit."""

import io
import zipfile

import streamlit as st

import ops

st.set_page_config(page_title="PDF Toolkit", page_icon="📄", layout="centered")

TOOLS = [
    "PDF to JPG",
    "Images to PDF",
    "Merge PDFs",
    "Split PDF",
    "Extract pages",
    "Delete pages",
    "Rotate pages",
    "Compress PDF",
    "Protect / Unlock",
    "Extract text",
    "PDF info",
]

PREVIEW_LIMIT = 20


# --- helpers ---------------------------------------------------------------


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    return buf.getvalue()


def upload_pdf(label="Upload a PDF", multiple=False):
    """File uploader plus a password box that appears only for locked PDFs."""
    up = st.file_uploader(label, type="pdf", accept_multiple_files=multiple)
    if multiple or not up:
        return up, None
    password = None
    try:
        ops.page_count(up.getvalue())
    except ValueError:
        password = st.text_input("This PDF is locked. Password:", type="password")
    return up, password


def run_button(key, signature, work, label="Run"):
    """Run `work` on click and remember the result across the reruns that
    downloading causes. A change to `signature` discards a stale result."""
    stored = st.session_state.get(key)
    if stored is not None and stored[0] != signature:
        st.session_state.pop(key, None)
        stored = None

    if st.button(label, type="primary"):
        try:
            with st.spinner("Working..."):
                st.session_state[key] = (signature, work())
            stored = st.session_state[key]
        except Exception as exc:  # surface the message instead of a traceback
            st.session_state.pop(key, None)
            st.error(str(exc))
            return None

    return stored[1] if stored else None


def offer(data, filename, mime="application/pdf", label=None):
    st.success("Done")
    st.download_button(label or f"Download {filename}", data, file_name=filename, mime=mime)


def stem(name):
    return name.rsplit(".", 1)[0]


def sig(up, *params):
    """A cheap fingerprint of the inputs, used to invalidate old results."""
    files = up if isinstance(up, list) else [up]
    return tuple((f.name, f.size) for f in files if f) + params


# --- tools -----------------------------------------------------------------


def tool_pdf_to_jpg():
    st.caption("Render every page as a JPG image.")
    up, pw = upload_pdf()
    c1, c2 = st.columns(2)
    dpi = c1.slider("DPI", 72, 400, ops.DPI)
    quality = c2.slider("JPG quality", 50, 100, ops.QUALITY)
    if not up:
        return

    pages = run_button(
        "jpg", sig(up, dpi, quality, pw),
        lambda: ops.pdf_to_jpgs(up.getvalue(), dpi=dpi, quality=quality, password=pw),
        "Convert",
    )
    if not pages:
        return

    st.success(f"{len(pages)} pages converted")
    st.download_button(
        "Download all as ZIP", zip_bytes(pages),
        file_name=f"{stem(up.name)}_jpg.zip", mime="application/zip",
    )
    for name, data in pages[:PREVIEW_LIMIT]:
        st.image(data, caption=name)
        st.download_button(f"Download {name}", data, file_name=name, mime="image/jpeg", key=name)
    if len(pages) > PREVIEW_LIMIT:
        st.info(f"Showing the first {PREVIEW_LIMIT} pages. The ZIP has all {len(pages)}.")


def tool_images_to_pdf():
    st.caption("Combine images into a single PDF, one image per page.")
    ups = st.file_uploader(
        "Upload images", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"],
        accept_multiple_files=True,
    )
    if not ups:
        return
    st.write("Pages will follow this order:")
    st.write(" → ".join(f.name for f in ups))

    data = run_button(
        "img2pdf", sig(ups),
        lambda: ops.images_to_pdf([(f.name, f.getvalue()) for f in ups]),
        "Create PDF",
    )
    if data:
        offer(data, "images.pdf")


def tool_merge():
    st.caption("Join several PDFs into one, in the order listed.")
    ups = st.file_uploader("Upload two or more PDFs", type="pdf", accept_multiple_files=True)
    if not ups:
        return
    st.write("Merge order:")
    st.write(" → ".join(f.name for f in ups))
    if len(ups) < 2:
        st.info("Add at least two PDFs.")
        return

    data = run_button(
        "merge", sig(ups),
        lambda: ops.merge_pdfs([(f.name, f.getvalue()) for f in ups]),
        "Merge",
    )
    if data:
        offer(data, "merged.pdf")


def tool_split():
    st.caption("Break a PDF into one file per page.")
    up, pw = upload_pdf()
    if not up:
        return

    parts = run_button(
        "split", sig(up, pw),
        lambda: ops.split_to_pages(up.getvalue(), password=pw),
        "Split",
    )
    if not parts:
        return
    st.success(f"Split into {len(parts)} files")
    st.download_button(
        "Download all as ZIP", zip_bytes(parts),
        file_name=f"{stem(up.name)}_split.zip", mime="application/zip",
    )


def _page_spec(up, pw, help_text):
    try:
        total = ops.page_count(up.getvalue(), pw)
    except ValueError as exc:
        st.error(str(exc))
        return None, None
    st.caption(f"This PDF has {total} pages.")
    return st.text_input("Pages", placeholder="e.g. 1-3, 5, 8-10", help=help_text), total


def tool_extract():
    st.caption("Keep only the pages you choose.")
    up, pw = upload_pdf()
    if not up:
        return
    spec, _ = _page_spec(up, pw, "Leave empty for every page.")
    if spec is None:
        return

    data = run_button(
        "extract", sig(up, spec, pw),
        lambda: ops.extract_pages(up.getvalue(), spec, password=pw),
        "Extract",
    )
    if data:
        offer(data, f"{stem(up.name)}_extracted.pdf")


def tool_delete():
    st.caption("Remove the pages you choose.")
    up, pw = upload_pdf()
    if not up:
        return
    spec, _ = _page_spec(up, pw, "These pages are removed.")
    if spec is None:
        return
    if not spec.strip():
        st.info("Enter the pages to delete.")
        return

    data = run_button(
        "delete", sig(up, spec, pw),
        lambda: ops.delete_pages(up.getvalue(), spec, password=pw),
        "Delete pages",
    )
    if data:
        offer(data, f"{stem(up.name)}_edited.pdf")


def tool_rotate():
    st.caption("Turn pages 90, 180 or 270 degrees.")
    up, pw = upload_pdf()
    if not up:
        return
    spec, _ = _page_spec(up, pw, "Leave empty to rotate every page.")
    if spec is None:
        return
    angle = st.radio("Rotate by", [90, 180, 270], horizontal=True, format_func=lambda a: f"{a}°")

    data = run_button(
        "rotate", sig(up, spec, angle, pw),
        lambda: ops.rotate_pages(up.getvalue(), spec, angle, password=pw),
        "Rotate",
    )
    if data:
        offer(data, f"{stem(up.name)}_rotated.pdf")


def tool_compress():
    st.caption("Make the file smaller.")
    up, pw = upload_pdf()
    mode = st.radio(
        "Method",
        ["Lossless cleanup", "Aggressive (rasterize pages)"],
        help="Lossless keeps text selectable. Rasterizing shrinks much more but turns "
             "every page into an image, so text can no longer be selected or searched.",
    )
    raster = mode.startswith("Aggressive")
    dpi, quality = 150, 70
    if raster:
        c1, c2 = st.columns(2)
        dpi = c1.slider("DPI", 72, 300, 150)
        quality = c2.slider("JPG quality", 30, 95, 70)
    if not up:
        return

    data = run_button(
        "compress", sig(up, raster, dpi, quality, pw),
        lambda: ops.compress(up.getvalue(), password=pw, rasterize=raster, dpi=dpi, quality=quality),
        "Compress",
    )
    if data is None:
        return

    before, after = up.size, len(data)
    change = (after - before) / before * 100
    st.metric("Size", f"{after / 1e6:.2f} MB", f"{change:.0f}% vs {before / 1e6:.2f} MB",
              delta_color="inverse")
    if after >= before:
        st.warning("This PDF is already well compressed -- the result is not smaller.")
    st.download_button("Download PDF", data, file_name=f"{stem(up.name)}_compressed.pdf",
                       mime="application/pdf")


def tool_password():
    st.caption("Add or remove a PDF password.")
    action = st.radio("Action", ["Add password", "Remove password"], horizontal=True)
    up = st.file_uploader("Upload a PDF", type="pdf")
    if not up:
        return

    if action == "Add password":
        new_pw = st.text_input("New password", type="password")
        data = run_button(
            "protect", sig(up, new_pw),
            lambda: ops.add_password(up.getvalue(), new_pw),
            "Protect",
        )
        if data:
            offer(data, f"{stem(up.name)}_protected.pdf")
    else:
        pw = st.text_input("Current password", type="password")
        data = run_button(
            "unlock", sig(up, pw),
            lambda: ops.remove_password(up.getvalue(), pw),
            "Unlock",
        )
        if data:
            offer(data, f"{stem(up.name)}_unlocked.pdf")


def tool_text():
    st.caption("Pull the text out of a PDF. Scanned pages have no text to extract.")
    up, pw = upload_pdf()
    if not up:
        return

    text = run_button(
        "text", sig(up, pw),
        lambda: ops.extract_text(up.getvalue(), password=pw),
        "Extract text",
    )
    if text is None:
        return
    if not text.replace("-", "").strip():
        st.warning("No text found. This PDF is probably scanned images -- OCR would be needed.")
    st.download_button("Download .txt", text, file_name=f"{stem(up.name)}.txt", mime="text/plain")
    st.text_area("Text", text, height=400)


def tool_info():
    st.caption("Inspect a PDF without changing it.")
    up, pw = upload_pdf()
    if not up:
        return
    try:
        info = ops.pdf_info(up.getvalue(), pw)
    except ValueError as exc:
        st.error(str(exc))
        return
    info["File size"] = f"{up.size / 1e6:.2f} MB"
    for key, value in info.items():
        st.write(f"**{key}:** {value}")


# --- main ------------------------------------------------------------------

RENDER = {
    "PDF to JPG": tool_pdf_to_jpg,
    "Images to PDF": tool_images_to_pdf,
    "Merge PDFs": tool_merge,
    "Split PDF": tool_split,
    "Extract pages": tool_extract,
    "Delete pages": tool_delete,
    "Rotate pages": tool_rotate,
    "Compress PDF": tool_compress,
    "Protect / Unlock": tool_password,
    "Extract text": tool_text,
    "PDF info": tool_info,
}

st.sidebar.title("📄 PDF Toolkit")
choice = st.sidebar.radio("Tool", TOOLS, label_visibility="collapsed")
st.sidebar.caption("Files are processed on this machine and are not uploaded anywhere.")

st.title(choice)
RENDER[choice]()
