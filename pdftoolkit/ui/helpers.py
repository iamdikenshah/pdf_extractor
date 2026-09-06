"""Shared UI helpers used across the tool pages."""

import io
import zipfile

import streamlit as st

from ..core import pdf_ops as ops

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"]

PREVIEW_LIMIT = 12



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



def _pages_input(up, pw, help_text):
    """Page-count caption plus the page selector. Returns None on a locked file."""
    try:
        total = ops.page_count(up.getvalue(), pw)
    except ValueError as exc:
        st.error(str(exc), icon=":material/lock:")
        return None
    st.caption(f"{up.name} · {total} pages · {human_size(up.size)}")
    return st.text_input("Pages", placeholder="e.g. 1-3, 5, 8-10", help=help_text)



def _image_uploads(label="Choose one or more images"):
    return st.file_uploader(label, type=IMAGE_TYPES, accept_multiple_files=True)



def _deliver_images(results, base_label, single_stem):
    """One download for a single result, a ZIP for several."""
    if len(results) == 1:
        name, data = results[0]
        st.image(data, caption=name)
        download(data, name, f"image/{name.rsplit('.', 1)[-1]}",
                 label=f"Download {name}", primary=True)
    else:
        download(zip_bytes(results), f"{single_stem}_images.zip", "application/zip",
                 f"Download all {len(results)} images (ZIP)", primary=True)
        for name, data in results[:PREVIEW_LIMIT]:
            st.image(data, caption=name)
        if len(results) > PREVIEW_LIMIT:
            st.info(f"Previewing the first {PREVIEW_LIMIT}. The ZIP has all {len(results)}.",
                    icon=":material/visibility:")



def _run_over_images(ups, per_image, key, signature, label, icon):
    """Apply per_image(bytes, name) -> (out_bytes, ext) to each upload."""
    def work():
        out = []
        for up in ups:
            data, ext = per_image(up.getvalue(), up.name)
            out.append((f"{stem(up.name)}.{ext}", data))
        return out
    return run_button(key, signature, work, label, icon)
