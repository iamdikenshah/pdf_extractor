"""Streamlit UI: upload a PDF, get one JPG per page."""

import io
import zipfile

import streamlit as st

from main import DPI, QUALITY, pdf_to_jpg_bytes

st.set_page_config(page_title="PDF to JPG", page_icon="🖼️")
st.title("PDF to JPG")

uploaded = st.file_uploader("Upload a PDF", type="pdf")

col1, col2 = st.columns(2)
dpi = col1.slider("DPI", 72, 400, DPI, step=1)
quality = col2.slider("JPG quality", 50, 100, QUALITY, step=1)

# Drop stale results if the file was removed or swapped for a different one.
file_key = (uploaded.name, uploaded.size) if uploaded else None
if file_key != st.session_state.get("file_key"):
    st.session_state.pop("pages", None)
    st.session_state["file_key"] = file_key

if st.button("Convert", type="primary", disabled=uploaded is None):
    with st.spinner("Converting..."):
        st.session_state["pages"] = list(
            pdf_to_jpg_bytes(uploaded.getvalue(), dpi=dpi, quality=quality)
        )

pages = st.session_state.get("pages")
if pages:
    st.success(f"{len(pages)} pages converted")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in pages:
            zf.writestr(name, data)

    st.download_button(
        "Download all as ZIP",
        buf.getvalue(),
        file_name=f"{uploaded.name.rsplit('.', 1)[0]}_jpg.zip",
        mime="application/zip",
    )

    for name, data in pages:
        st.image(data, caption=name)
        st.download_button(f"Download {name}", data, file_name=name, mime="image/jpeg", key=name)
