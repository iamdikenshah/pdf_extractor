"""Inspect: show a PDF's metadata."""

import streamlit as st
from ...core import pdf_ops as ops
from .. import theme as ui
from ..helpers import human_size, upload_pdf


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



PAGES = {
    "PDF info": tool_info,
}
