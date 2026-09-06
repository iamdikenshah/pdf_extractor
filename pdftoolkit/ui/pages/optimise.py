"""Optimise: shrink a PDF's file size."""

import streamlit as st
from ...core import pdf_ops as ops
from .. import theme as ui
from ..helpers import human_size, stem, sig, upload_pdf, run_button, result_card, download, file_meta


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



PAGES = {
    "Compress PDF": tool_compress,
}
