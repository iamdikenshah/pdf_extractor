"""Full screen page editor: click a line of text to rewrite it."""

import io

import streamlit as st
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates as image_click

import ops
import ui

CANVAS_WIDTH = 820
TOOLS = {"Edit text": "edit_note", "Add text": "text_fields"}
HINTS = {
    "Edit text": "Click a line of text on the page to rewrite it.",
    "Add text": "Click where the new text should start.",
}


# --- state -----------------------------------------------------------------


def _start(up):
    """Load a file into the editor, unlocking it first if needed."""
    signature = (up.name, up.size)
    if st.session_state.get("ed_sig") == signature:
        return True

    data = up.getvalue()
    try:
        ops.page_count(data)
    except ValueError:
        st.warning("This PDF is password protected.", icon=":material/lock:")
        pw = st.text_input("Password", type="password", key="ed_pw")
        if not pw:
            return False
        try:
            data = ops.remove_password(data, pw)
        except ValueError as exc:
            st.error(str(exc), icon=":material/lock:")
            return False

    st.session_state.update(
        ed_sig=signature, ed_name=up.name, ed_doc=data, ed_draft=data,
        ed_page=0, ed_dirty=False, ed_undo=[], ed_click=None, ed_target=None,
        ed_span=None, ed_rev=0,
    )
    return True


def _bump():
    """Widgets keyed on this reset when the page content changes underneath them."""
    st.session_state.ed_rev = st.session_state.get("ed_rev", 0) + 1


def _commit():
    st.session_state.ed_doc = st.session_state.ed_draft
    st.session_state.ed_dirty = False
    st.session_state.ed_undo = []
    st.session_state.ed_span = None
    _bump()


def _revert():
    st.session_state.ed_draft = st.session_state.ed_doc
    st.session_state.ed_dirty = False
    st.session_state.ed_undo = []
    st.session_state.ed_span = None
    _bump()


def _edit(new_bytes):
    st.session_state.ed_undo.append(st.session_state.ed_draft)
    st.session_state.ed_draft = new_bytes
    st.session_state.ed_dirty = True
    st.session_state.ed_span = None
    _bump()


def _goto(index):
    st.session_state.ed_page = index
    st.session_state.ed_target = None
    st.session_state.ed_span = None


@st.dialog("Keep your changes?")
def _keep_dialog():
    page = st.session_state.ed_page + 1
    target = st.session_state.ed_target
    st.write(f"Page {page} has changes you have not saved yet.")
    if st.button("Keep them and continue", type="primary", width="stretch",
                 icon=":material/check:"):
        _commit()
        _goto(target)
        st.rerun()
    if st.button("Discard them and continue", width="stretch", icon=":material/undo:"):
        _revert()
        _goto(target)
        st.rerun()
    if st.button("Stay on this page", width="stretch"):
        st.session_state.ed_target = None
        st.rerun()


def _leave(target):
    """Move to another page, asking about unsaved work first."""
    if st.session_state.ed_dirty:
        st.session_state.ed_target = target
    else:
        _goto(target)
    st.rerun()


# --- panels ----------------------------------------------------------------


@st.cache_data(show_spinner=False, max_entries=30)
def _render(data, index, width):
    return ops.render_page_px(data, index, width_px=width)


def _edit_text_panel(page):
    """Rewrite one run of text, picked on the page or from the list."""
    data = st.session_state.ed_draft
    spans = ops.page_spans(data, page)
    if not spans:
        st.info("No editable text on this page. Scanned pages hold images, not text.",
                icon=":material/scanner:")
        return

    labels = [s["text"].strip()[:60] for s in spans]
    picked = st.session_state.ed_span
    default = picked if isinstance(picked, int) and picked < len(spans) else 0
    rev = st.session_state.get("ed_rev", 0)
    index = st.selectbox("Text on this page", range(len(spans)), index=default,
                         format_func=lambda i: labels[i], key=f"ed_pick_{page}_{rev}")
    span = spans[index]

    new_text = st.text_input("Replace with", value=span["text"],
                             key=f"ed_val_{page}_{index}_{rev}")
    if st.button("Replace text", type="primary", width="stretch", icon=":material/check:"):
        try:
            _edit(ops.replace_span(data, page, span["bbox"], new_text,
                                   span["size"], span["color"]))
            st.rerun()
        except Exception as exc:
            st.error(str(exc), icon=":material/error:")
    st.caption("The replacement is set in Helvetica at the original size: a PDF's "
               "embedded fonts usually cannot be reused for new text.")


def _add_text_panel():
    return {
        "text": st.text_area("Text", key="ed_t_text", height=90,
                             placeholder="Type what you want to add, then click the page"),
        "size": st.slider("Size", 6, 60, 14, key="ed_t_size"),
        "color": st.color_picker("Colour", "#1B1F35", key="ed_t_col"),
        "opacity": st.slider("Opacity", 0.1, 1.0, 1.0, 0.05, key="ed_t_op"),
    }


# --- the page --------------------------------------------------------------


def _canvas(page, tool, settings):
    """The page image. Returns True when something changed."""
    data = st.session_state.ed_draft
    png, _ = _render(data, page, CANVAS_WIDTH)
    value = image_click(Image.open(io.BytesIO(png)), key=f"ed_canvas_{page}",
                        cursor="crosshair")
    if not value:
        return False

    stamp = value.get("unix_time")
    if stamp == st.session_state.get("ed_click"):
        return False
    st.session_state.ed_click = stamp

    shown = value.get("width") or CANVAS_WIDTH
    page_w, _ = ops.page_size(data, page)
    scale = page_w / shown
    point = (value["x"] * scale, value["y"] * scale)

    if tool == "Edit text":
        span = ops.span_at(data, page, point)
        if span is None:
            st.toast("No text there. Click directly on a line of text.",
                     icon=":material/info:")
            return False
        spans = ops.page_spans(data, page)
        st.session_state.ed_span = next(
            (i for i, s in enumerate(spans) if s["bbox"] == span["bbox"]), 0)
        return True

    try:
        _edit(ops.add_text_at(data, page, point, settings["text"], settings["size"],
                              settings["color"], settings["opacity"]))
        return True
    except Exception as exc:
        st.error(str(exc), icon=":material/error:")
        return False


# --- main ------------------------------------------------------------------


def render():
    st.markdown("<style>.stMainBlockContainer{max-width:1500px;}</style>",
                unsafe_allow_html=True)

    with st.container(border=True):
        up = st.file_uploader("Choose the PDF you want to edit", type="pdf", key="ed_file")
        if not up:
            st.session_state.pop("ed_sig", None)
            st.caption("Tip: collapse the sidebar with « for more room.")
            return
        if not _start(up):
            return

    if st.session_state.ed_target is not None:
        _keep_dialog()

    data = st.session_state.ed_draft
    total = ops.page_count(data)
    page = min(st.session_state.ed_page, total - 1)
    st.session_state.ed_page = page

    tools, canvas = st.columns([0.42, 1], gap="medium")

    with tools:
        with st.container(border=True):
            ui.step(1, "Pick a tool")
            tool = st.pills("Tool", list(TOOLS), default="Edit text", key="ed_tool",
                            label_visibility="collapsed") or "Edit text"
            st.caption(HINTS[tool])
            st.markdown("")
            settings = {}
            if tool == "Edit text":
                _edit_text_panel(page)
            else:
                settings = _add_text_panel()

        with st.container(border=True):
            ui.step(2, "This page")
            c1, c2 = st.columns(2)
            if c1.button("Undo", icon=":material/undo:", width="stretch",
                         disabled=not st.session_state.ed_undo):
                st.session_state.ed_draft = st.session_state.ed_undo.pop()
                st.session_state.ed_dirty = bool(st.session_state.ed_undo)
                _bump()
                st.rerun()
            if c2.button("Revert page", icon=":material/restart_alt:", width="stretch",
                         disabled=not st.session_state.ed_dirty):
                _revert()
                st.rerun()
            if st.button("Save this page", type="primary", width="stretch",
                         icon=":material/save:", disabled=not st.session_state.ed_dirty):
                _commit()
                st.toast("Page saved", icon=":material/check_circle:")
                st.rerun()
            st.caption("Unsaved changes on this page" if st.session_state.ed_dirty
                       else "No unsaved changes")

        with st.container(border=True):
            st.download_button(
                "Download PDF", data,
                file_name=f"{st.session_state.ed_name.rsplit('.', 1)[0]}_edited.pdf",
                mime="application/pdf", icon=":material/download:",
                type="primary", width="stretch")
            st.caption("Includes everything you see, saved or not.")

    with canvas:
        with st.container(border=True):
            left, middle, right = st.columns([1, 1.4, 1])
            if left.button("Previous", icon=":material/chevron_left:", width="stretch",
                           disabled=page == 0):
                _leave(page - 1)
            middle.markdown(
                f"<div style='text-align:center;font-weight:640;padding-top:.45rem;'>"
                f"Page {page + 1} of {total}"
                f"{' · unsaved' if st.session_state.ed_dirty else ''}</div>",
                unsafe_allow_html=True)
            if right.button("Next", icon=":material/chevron_right:", width="stretch",
                            disabled=page >= total - 1):
                _leave(page + 1)

            if _canvas(page, tool, settings):
                st.rerun()
