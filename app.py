"""PDF Toolkit -- Streamlit entrypoint.

Thin composition root: it wires the presentation layer (pdftoolkit.ui) to the
tool pages and runs the selected one. All logic lives in pdftoolkit.core, all
chrome in pdftoolkit.ui.
"""

import streamlit as st

from pdftoolkit.ui import theme
from pdftoolkit.ui.pages import PAGES

theme.setup()
st.session_state.setdefault("tool", "PDF to JPG")
# A session from before a tool was removed could still point at it; fall back.
if st.session_state.tool not in PAGES:
    st.session_state.tool = "PDF to JPG"

tool = theme.sidebar_nav(st.session_state.tool)
theme.page_head(tool)
PAGES[tool]()
