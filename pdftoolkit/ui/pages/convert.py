"""Convert tools: PDF to JPG, images to PDF, extract text."""

import streamlit as st
from ...core import pdf_ops as ops
from .. import theme as ui
from ..helpers import PREVIEW_LIMIT, zip_bytes, stem, sig, upload_pdf, run_button, result_card, download, file_meta


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



PAGES = {
    "PDF to JPG": tool_pdf_to_jpg,
    "Images to PDF": tool_images_to_pdf,
    "Extract text": tool_text,
}
