"""Batch editor ("Apply to all pages"). Kept but not shown in the menu;
add {"Apply to all pages": tool_edit} to PAGES and a registry entry to restore it."""

import streamlit as st
from ...core import pdf_ops as ops
from .. import theme as ui
from ..helpers import human_size, stem, download


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
            action = st.pills("Action", EDIT_ACTIONS, default=EDIT_ACTIONS[0],
                              label_visibility="collapsed") or EDIT_ACTIONS[0]
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
