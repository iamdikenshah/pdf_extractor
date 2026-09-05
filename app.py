"""PDF Toolkit -- Streamlit interface."""

import io
import zipfile

import streamlit as st

import ops
import ui

PREVIEW_LIMIT = 12


# --- helpers ---------------------------------------------------------------


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    return buf.getvalue()


def human_size(num):
    return f"{num / 1e6:.2f} MB" if num >= 1e6 else f"{num / 1e3:.0f} KB"


def stem(name):
    return name.rsplit(".", 1)[0]


def sig(up, *params):
    """A cheap fingerprint of the inputs, used to discard stale results."""
    files = up if isinstance(up, list) else [up]
    return tuple((f.name, f.size) for f in files if f) + params


def upload_pdf(label="Choose a PDF file", multiple=False):
    """Uploader plus a password box that appears only when the PDF is locked."""
    up = st.file_uploader(label, type="pdf", accept_multiple_files=multiple)
    if multiple or not up:
        return up, None
    password = None
    try:
        ops.page_count(up.getvalue())
    except ValueError:
        st.warning("This PDF is password protected.", icon=":material/lock:")
        password = st.text_input("Password", type="password", placeholder="Enter the password")
    return up, password


def run_button(key, signature, work, label="Run", icon=None):
    """Run `work` on click and remember the result across the reruns that
    downloading causes. A change to `signature` discards a stale result."""
    stored = st.session_state.get(key)
    if stored is not None and stored[0] != signature:
        st.session_state.pop(key, None)
        stored = None

    if st.button(label, type="primary", icon=icon, width="stretch"):
        try:
            with st.spinner("Working on it..."):
                st.session_state[key] = (signature, work())
            stored = st.session_state[key]
        except Exception as exc:  # show the message, not a traceback
            st.session_state.pop(key, None)
            st.error(str(exc), icon=":material/error:")
            return None

    return stored[1] if stored else None


def result_card(message):
    st.markdown("")
    st.success(message, icon=":material/check_circle:")


def download(data, filename, mime="application/pdf", label=None, primary=False):
    st.download_button(
        label or "Download",
        data,
        file_name=filename,
        mime=mime,
        icon=":material/download:",
        width="stretch",
        type="primary" if primary else "secondary",
    )


def file_meta(up):
    st.caption(f"{up.name} · {human_size(up.size)}")


# --- tools -----------------------------------------------------------------


def tool_pdf_to_jpg():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if up:
            file_meta(up)

        ui.step(2, "Image settings")
        c1, c2 = st.columns(2)
        dpi = c1.slider("Resolution (DPI)", 72, 400, ops.DPI,
                        help="150 for screen, 300 for print.")
        quality = c2.slider("JPG quality", 50, 100, ops.QUALITY)

        if not up:
            return
        ui.step(3, "Convert")
        pages = run_button(
            "jpg", sig(up, dpi, quality, pw),
            lambda: ops.pdf_to_jpgs(up.getvalue(), dpi=dpi, quality=quality, password=pw),
            "Convert to JPG", ":material/bolt:",
        )

    if not pages:
        return
    result_card(f"{len(pages)} pages converted")
    with st.container(border=True):
        download(zip_bytes(pages), f"{stem(up.name)}_jpg.zip", "application/zip",
                 f"Download all {len(pages)} images (ZIP)", primary=True)
        st.markdown("")
        for name, data in pages[:PREVIEW_LIMIT]:
            st.image(data, caption=name)
            download(data, name, "image/jpeg", f"Download {name}")
        if len(pages) > PREVIEW_LIMIT:
            st.info(f"Previewing the first {PREVIEW_LIMIT} pages. "
                    f"The ZIP contains all {len(pages)}.", icon=":material/visibility:")


def tool_images_to_pdf():
    with st.container(border=True):
        ui.step(1, "Choose your images")
        ups = st.file_uploader(
            "Images", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"],
            accept_multiple_files=True,
        )
        if not ups:
            return
        ui.step(2, "Page order")
        ui.chips([f.name for f in ups])
        st.caption("Pages follow the order shown. Re-upload in a different order to change it.")

        ui.step(3, "Create")
        data = run_button(
            "img2pdf", sig(ups),
            lambda: ops.images_to_pdf([(f.name, f.getvalue()) for f in ups]),
            "Create PDF", ":material/picture_as_pdf:",
        )

    if data:
        result_card(f"PDF created from {len(ups)} images")
        with st.container(border=True):
            download(data, "images.pdf", label="Download PDF", primary=True)


def tool_merge():
    with st.container(border=True):
        ui.step(1, "Choose two or more PDFs")
        ups = st.file_uploader("PDF files", type="pdf", accept_multiple_files=True)
        if not ups:
            return
        ui.step(2, "Merge order")
        ui.chips([f.name for f in ups])
        if len(ups) < 2:
            st.info("Add at least one more PDF to merge.", icon=":material/add:")
            return

        ui.step(3, "Merge")
        data = run_button(
            "merge", sig(ups),
            lambda: ops.merge_pdfs([(f.name, f.getvalue()) for f in ups]),
            "Merge PDFs", ":material/merge:",
        )

    if data:
        result_card(f"{len(ups)} files merged into one")
        with st.container(border=True):
            download(data, "merged.pdf", label="Download merged PDF", primary=True)


def tool_split():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        file_meta(up)

        ui.step(2, "Split")
        parts = run_button(
            "split", sig(up, pw),
            lambda: ops.split_to_pages(up.getvalue(), password=pw),
            "Split into single pages", ":material/content_cut:",
        )

    if parts:
        result_card(f"Split into {len(parts)} files")
        with st.container(border=True):
            download(zip_bytes(parts), f"{stem(up.name)}_split.zip", "application/zip",
                     f"Download all {len(parts)} PDFs (ZIP)", primary=True)


def _pages_input(up, pw, help_text):
    """Page-count caption plus the page selector. Returns None on a locked file."""
    try:
        total = ops.page_count(up.getvalue(), pw)
    except ValueError as exc:
        st.error(str(exc), icon=":material/lock:")
        return None
    st.caption(f"{up.name} · {total} pages · {human_size(up.size)}")
    return st.text_input("Pages", placeholder="e.g. 1-3, 5, 8-10", help=help_text)


def tool_extract():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        ui.step(2, "Pages to keep")
        spec = _pages_input(up, pw, "Leave empty to keep every page.")
        if spec is None:
            return

        ui.step(3, "Extract")
        data = run_button(
            "extract", sig(up, spec, pw),
            lambda: ops.extract_pages(up.getvalue(), spec, password=pw),
            "Extract pages", ":material/file_copy:",
        )

    if data:
        result_card("Pages extracted")
        with st.container(border=True):
            download(data, f"{stem(up.name)}_extracted.pdf", label="Download PDF", primary=True)


def tool_delete():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        ui.step(2, "Pages to remove")
        spec = _pages_input(up, pw, "These pages are deleted. Everything else is kept.")
        if spec is None:
            return
        if not spec.strip():
            st.info("Enter which pages to delete.", icon=":material/edit:")
            return

        ui.step(3, "Delete")
        data = run_button(
            "delete", sig(up, spec, pw),
            lambda: ops.delete_pages(up.getvalue(), spec, password=pw),
            "Delete pages", ":material/delete:",
        )

    if data:
        result_card("Pages removed")
        with st.container(border=True):
            download(data, f"{stem(up.name)}_edited.pdf", label="Download PDF", primary=True)


def tool_rotate():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        ui.step(2, "Pages to rotate")
        spec = _pages_input(up, pw, "Leave empty to rotate every page.")
        if spec is None:
            return

        ui.step(3, "Direction")
        angle = st.radio("Rotate by", [90, 180, 270], horizontal=True,
                         format_func=lambda a: f"{a}°", label_visibility="collapsed")

        data = run_button(
            "rotate", sig(up, spec, angle, pw),
            lambda: ops.rotate_pages(up.getvalue(), spec, angle, password=pw),
            "Rotate pages", ":material/rotate_right:",
        )

    if data:
        result_card("Pages rotated")
        with st.container(border=True):
            download(data, f"{stem(up.name)}_rotated.pdf", label="Download PDF", primary=True)


def tool_compress():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if up:
            file_meta(up)

        ui.step(2, "Method")
        mode = st.radio(
            "Method",
            ["Lossless cleanup", "Aggressive (rasterise pages)"],
            label_visibility="collapsed",
            captions=[
                "Safe. Text stays selectable and searchable.",
                "Much smaller files, but pages become images.",
            ],
        )
        raster = mode.startswith("Aggressive")
        dpi, quality = 150, 70
        if raster:
            c1, c2 = st.columns(2)
            dpi = c1.slider("Resolution (DPI)", 72, 300, 150)
            quality = c2.slider("JPG quality", 30, 95, 70)

        if not up:
            return
        ui.step(3, "Compress")
        data = run_button(
            "compress", sig(up, raster, dpi, quality, pw),
            lambda: ops.compress(up.getvalue(), password=pw, rasterize=raster,
                                 dpi=dpi, quality=quality),
            "Compress PDF", ":material/compress:",
        )

    if data is None:
        return
    before, after = up.size, len(data)
    change = (after - before) / before * 100
    result_card("Compression finished")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.metric("Before", human_size(before))
        c2.metric("After", human_size(after), f"{change:.0f}%", delta_color="inverse")
        if after >= before:
            st.warning("This PDF is already well optimised, so it did not get smaller. "
                       "Try the aggressive method.", icon=":material/info:")
        st.markdown("")
        download(data, f"{stem(up.name)}_compressed.pdf", label="Download PDF", primary=True)


def tool_password():
    with st.container(border=True):
        ui.step(1, "What do you want to do?")
        action = st.radio("Action", ["Add a password", "Remove a password"],
                          horizontal=True, label_visibility="collapsed")
        ui.step(2, "Choose your PDF")
        up = st.file_uploader("PDF file", type="pdf")
        if not up:
            return
        file_meta(up)

        if action == "Add a password":
            ui.step(3, "Set the password")
            new_pw = st.text_input("New password", type="password",
                                   placeholder="Choose a strong password")
            data = run_button(
                "protect", sig(up, new_pw),
                lambda: ops.add_password(up.getvalue(), new_pw),
                "Protect PDF", ":material/lock:",
            )
            name, note = f"{stem(up.name)}_protected.pdf", "Password added (AES-256)"
        else:
            ui.step(3, "Enter the current password")
            pw = st.text_input("Current password", type="password")
            data = run_button(
                "unlock", sig(up, pw),
                lambda: ops.remove_password(up.getvalue(), pw),
                "Unlock PDF", ":material/lock_open:",
            )
            name, note = f"{stem(up.name)}_unlocked.pdf", "Password removed"

    if data:
        result_card(note)
        with st.container(border=True):
            download(data, name, label="Download PDF", primary=True)


def tool_text():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        file_meta(up)

        ui.step(2, "Extract")
        text = run_button(
            "text", sig(up, pw),
            lambda: ops.extract_text(up.getvalue(), password=pw),
            "Extract text", ":material/notes:",
        )

    if text is None:
        return
    if not text.replace("-", "").replace("Page", "").strip().strip("0123456789"):
        st.warning("No text found. This PDF is most likely made of scanned images, "
                   "which need OCR.", icon=":material/scanner:")
    result_card(f"{len(text.split())} words extracted")
    with st.container(border=True):
        download(text, f"{stem(up.name)}.txt", "text/plain",
                 "Download as .txt", primary=True)
        st.text_area("Preview", text, height=380, label_visibility="collapsed")


def tool_info():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        try:
            info = ops.pdf_info(up.getvalue(), pw)
        except ValueError as exc:
            st.error(str(exc), icon=":material/lock:")
            return

    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.metric("Pages", info["Pages"])
        c2.metric("File size", human_size(up.size))
        st.markdown("")
        ui.info_rows(
            [("File name", up.name)]
            + [(k, v) for k, v in info.items() if k != "Pages"]
        )


# --- editor ----------------------------------------------------------------

EDIT_ACTIONS = [
    "Add text", "Add image or signature", "Add watermark", "Add page numbers",
    "Highlight text", "Redact text", "Reorder pages",
]


@st.cache_data(show_spinner=False, max_entries=24)
def preview_page(data, index, dpi=110):
    return ops.render_preview(data, index, dpi=dpi)


def edit_current():
    return st.session_state.edit_stack[-1]


def edit_apply(label, icon, key, work):
    """Run an edit, push it onto the history, and refresh the preview."""
    if not st.button(label, icon=icon, type="primary", width="stretch", key=key):
        return
    try:
        with st.spinner("Applying..."):
            result = work(edit_current())
        data, note = result if isinstance(result, tuple) else (result, "Change applied")
        st.session_state.edit_stack.append(data)
        st.toast(note, icon=":material/check_circle:")
        st.rerun()
    except Exception as exc:
        st.error(str(exc), icon=":material/error:")


def edit_start(up):
    """Begin (or restart) an editing session for the uploaded file."""
    signature = (up.name, up.size)
    if st.session_state.get("edit_sig") == signature:
        return True

    data = up.getvalue()
    try:
        ops.page_count(data)
    except ValueError:
        st.warning("This PDF is password protected.", icon=":material/lock:")
        pw = st.text_input("Password", type="password", key="edit_pw")
        if not pw:
            return False
        try:
            data = ops.remove_password(data, pw)
            st.caption("Unlocked. The edited copy will be saved without the password.")
        except ValueError as exc:
            st.error(str(exc), icon=":material/lock:")
            return False

    st.session_state.edit_sig = signature
    st.session_state.edit_stack = [data]
    st.session_state.edit_page = 1
    return True


def tool_edit():
    with st.container(border=True):
        ui.step(1, "Choose the PDF you want to edit")
        up = st.file_uploader("PDF file", type="pdf")
        if not up:
            st.session_state.pop("edit_sig", None)
            return
        if not edit_start(up):
            return

    data = edit_current()
    total = ops.page_count(data)
    edits = len(st.session_state.edit_stack) - 1

    controls, preview = st.columns([1, 0.9], gap="medium")

    with controls:
        with st.container(border=True):
            ui.step(2, "Choose what to change")
            action = st.selectbox("Action", EDIT_ACTIONS, label_visibility="collapsed")
            st.markdown("")
            EDIT_RENDER[action](total)

        with st.container(border=True):
            c1, c2 = st.columns(2)
            if c1.button("Undo", icon=":material/undo:", width="stretch",
                         disabled=edits == 0):
                st.session_state.edit_stack.pop()
                st.rerun()
            if c2.button("Start over", icon=":material/restart_alt:", width="stretch",
                         disabled=edits == 0):
                del st.session_state.edit_stack[1:]
                st.rerun()
            st.caption(f"{edits} change{'s' if edits != 1 else ''} applied")
            download(data, f"{stem(up.name)}_edited.pdf",
                     label="Download edited PDF", primary=True)

    with preview:
        with st.container(border=True):
            head, nav = st.columns([1, 1])
            head.markdown("**Live preview**")
            page = nav.number_input("Page", 1, total, min(st.session_state.edit_page, total),
                                    label_visibility="collapsed")
            st.session_state.edit_page = page
            st.image(preview_page(data, page - 1))
            st.caption(f"Page {page} of {total} · {human_size(len(data))}")


def _pages_field(total, label="Pages", help_text="Leave empty for every page."):
    return st.text_input(label, placeholder=f"all pages (1-{total})", help=help_text)


def _position_field(default="Bottom centre"):
    c1, c2 = st.columns([1, 1])
    position = c1.selectbox("Position", ops.POSITIONS, index=ops.POSITIONS.index(default))
    margin = c2.slider("Margin (pt)", 0, 120, 36)
    return position, margin


def edit_add_text(total):
    text = st.text_area("Text", placeholder="Approved by...", height=90)
    position, margin = _position_field("Top right")
    c1, c2 = st.columns(2)
    size = c1.slider("Size", 6, 72, 14)
    colour = c2.color_picker("Colour", "#1B1F35")
    opacity = st.slider("Opacity", 0.1, 1.0, 1.0, 0.05)
    spec = _pages_field(total)
    edit_apply("Add text", ":material/title:", "e_text",
               lambda d: ops.add_text(d, spec, text, position, size, colour, opacity, margin))


def edit_add_image(total):
    img = st.file_uploader("Image", type=["png", "jpg", "jpeg", "webp"], key="edit_img")
    st.caption("A PNG with a transparent background works best for signatures.")
    position, margin = _position_field("Bottom right")
    c1, c2 = st.columns(2)
    width = c1.slider("Width (% of page)", 5, 100, 25)
    opacity = c2.slider("Opacity", 0.1, 1.0, 1.0, 0.05, key="img_op")
    spec = _pages_field(total)
    if not img:
        st.info("Upload an image to place on the page.", icon=":material/image:")
        return
    edit_apply("Place image", ":material/add_photo_alternate:", "e_img",
               lambda d: ops.add_image(d, spec, img.getvalue(), position, width,
                                       opacity, margin))


def edit_watermark(total):
    text = st.text_input("Watermark text", value="DRAFT")
    c1, c2 = st.columns(2)
    size = c1.slider("Size", 20, 140, 60)
    angle = c2.slider("Angle", 0, 90, 45)
    c3, c4 = st.columns(2)
    colour = c3.color_picker("Colour", "#9AA0BD", key="wm_col")
    opacity = c4.slider("Opacity", 0.05, 1.0, 0.25, 0.05, key="wm_op")
    spec = _pages_field(total)
    edit_apply("Add watermark", ":material/branding_watermark:", "e_wm",
               lambda d: ops.add_watermark(d, text, spec, size, colour, opacity, angle))


def edit_page_numbers(total):
    style = st.selectbox("Style", list(ops.NUMBER_FORMATS))
    position, margin = _position_field("Bottom centre")
    c1, c2 = st.columns(2)
    start = c1.number_input("Start at", 1, 9999, 1)
    size = c2.slider("Size", 6, 24, 10, key="pn_size")
    c3, c4 = st.columns(2)
    colour = c3.color_picker("Colour", "#6B7192", key="pn_col")
    skip = c4.checkbox("Skip the first page")
    edit_apply("Add page numbers", ":material/tag:", "e_pn",
               lambda d: ops.add_page_numbers(d, position, start, ops.NUMBER_FORMATS[style],
                                              size, colour, margin, skip))


def edit_highlight(total):
    query = st.text_input("Text to highlight")
    colour = st.color_picker("Highlight colour", "#FFE066", key="hl_col")
    if query:
        try:
            found = ops.find_text(edit_current(), query)
            st.caption(f"Found {sum(n for _, n in found)} times on "
                       f"{len(found)} page{'s' if len(found) != 1 else ''}."
                       if found else "Not found in this PDF.")
        except ValueError:
            pass
    edit_apply("Highlight", ":material/format_ink_highlighter:", "e_hl",
               lambda d: (lambda r: (r[0], f"Highlighted {r[1]} matches"))(
                   ops.highlight_text(d, query, colour)))


def edit_redact(total):
    query = st.text_input("Text to remove permanently")
    colour = st.color_picker("Box colour", "#000000", key="rd_col")
    st.warning("Redaction deletes the text from the file, not just hides it. "
               "This cannot be undone once you download.", icon=":material/warning:")
    if query:
        try:
            found = ops.find_text(edit_current(), query)
            st.caption(f"Found {sum(n for _, n in found)} times on "
                       f"{len(found)} page{'s' if len(found) != 1 else ''}."
                       if found else "Not found in this PDF.")
        except ValueError:
            pass
    edit_apply("Redact", ":material/ink_eraser:", "e_rd",
               lambda d: (lambda r: (r[0], f"Redacted {r[1]} matches"))(
                   ops.redact_text(d, query, colour)))


def edit_reorder(total):
    st.caption(f"This PDF has {total} pages. Give the new order, for example "
               f"`{total},1-{max(total - 1, 1)}` to move the last page to the front.")
    spec = st.text_input("New page order", placeholder=f"1-{total}")
    if not spec.strip():
        st.info("Enter the order you want.", icon=":material/reorder:")
        return
    edit_apply("Apply order", ":material/reorder:", "e_ro",
               lambda d: ops.reorder_pages(d, spec))


EDIT_RENDER = {
    "Add text": edit_add_text,
    "Add image or signature": edit_add_image,
    "Add watermark": edit_watermark,
    "Add page numbers": edit_page_numbers,
    "Highlight text": edit_highlight,
    "Redact text": edit_redact,
    "Reorder pages": edit_reorder,
}


# --- main ------------------------------------------------------------------

RENDER = {
    "PDF to JPG": tool_pdf_to_jpg,
    "Images to PDF": tool_images_to_pdf,
    "Extract text": tool_text,
    "Edit PDF": tool_edit,
    "Merge PDFs": tool_merge,
    "Split PDF": tool_split,
    "Extract pages": tool_extract,
    "Delete pages": tool_delete,
    "Rotate pages": tool_rotate,
    "Compress PDF": tool_compress,
    "Protect / Unlock": tool_password,
    "PDF info": tool_info,
}

ui.setup()
st.session_state.setdefault("tool", "PDF to JPG")
tool = ui.sidebar_nav(st.session_state.tool)

ui.page_head(tool)
RENDER[tool]()
