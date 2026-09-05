"""Presentation helpers: theme, icons, page chrome."""

from pathlib import Path

import streamlit as st

# Tool -> (Material icon, one-line description)
TOOLS = {
    "PDF to JPG": ("image", "Render every page as a high quality JPG image."),
    "Images to PDF": ("picture_as_pdf", "Combine images into a single PDF, one per page."),
    "Extract text": ("notes", "Pull the text out of a PDF and save it as a file."),
    "Edit PDF": ("edit_document",
                 "Add text, images, watermarks and page numbers, highlight, redact and reorder."),
    "Merge PDFs": ("merge", "Join several PDFs into one, in the order you choose."),
    "Split PDF": ("content_cut", "Break a PDF into one separate file per page."),
    "Extract pages": ("file_copy", "Keep only the pages you select."),
    "Delete pages": ("delete", "Remove the pages you no longer need."),
    "Rotate pages": ("rotate_right", "Turn pages 90, 180 or 270 degrees."),
    "Compress PDF": ("compress", "Shrink the file size of a PDF."),
    "Protect / Unlock": ("lock", "Add a password, or remove one you know."),
    "PDF info": ("info", "Inspect a document without changing it."),
}

# Sidebar grouping
GROUPS = {
    "Convert": ["PDF to JPG", "Images to PDF", "Extract text"],
    "Edit": ["Edit PDF"],
    "Organise": ["Merge PDFs", "Split PDF", "Extract pages", "Delete pages", "Rotate pages"],
    "Optimise": ["Compress PDF"],
    "Secure": ["Protect / Unlock"],
    "Inspect": ["PDF info"],
}

_LOGO = """<svg width="21" height="21" viewBox="0 0 24 24" fill="none"
 stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
<polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/>
</svg>"""


def setup():
    """Page config and stylesheet. Call once, first thing."""
    st.set_page_config(
        page_title="PDF Toolkit",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    css = Path(__file__).with_name("styles.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def sidebar_nav(current):
    """Brand block plus grouped nav. Returns the selected tool."""
    with st.sidebar:
        st.markdown(
            f"""<div class="brand">
                <div class="brand-badge">{_LOGO}</div>
                <div><div class="brand-name">PDF Toolkit</div>
                <div class="brand-tag">Eleven tools, one place</div></div>
            </div>""",
            unsafe_allow_html=True,
        )

        for group, tools in GROUPS.items():
            st.markdown(f'<div class="nav-group">{group}</div>', unsafe_allow_html=True)
            for tool in tools:
                icon, _ = TOOLS[tool]
                if st.button(
                    tool,
                    icon=f":material/{icon}:",
                    key=f"nav_{tool}",
                    type="primary" if tool == current else "tertiary",
                    width="stretch",
                ):
                    st.session_state.tool = tool
                    st.rerun()

        st.markdown(
            '<div class="side-note">🔒 Everything runs on this computer. '
            'Your files are never uploaded to a server.</div>',
            unsafe_allow_html=True,
        )
    return st.session_state.get("tool", current)


def page_head(tool):
    icon, description = TOOLS[tool]
    st.markdown(
        f"""<div class="page-head">
            <div class="page-icon">
              <span class="msr">{icon}</span>
            </div>
            <div class="page-title">{tool}</div>
        </div>
        <p class="page-sub">{description}</p>""",
        unsafe_allow_html=True,
    )


def step(number, text):
    """A small numbered step label inside a card."""
    st.markdown(
        f'<div style="font-weight:640;font-size:.9rem;color:#3A4062;margin:.1rem 0 .5rem;">'
        f'<span class="chip-num">{number}</span>{text}</div>',
        unsafe_allow_html=True,
    )


def chips(items):
    st.markdown(
        '<div class="chip-row">' + "".join(f'<span class="chip">{i}</span>' for i in items) + "</div>",
        unsafe_allow_html=True,
    )


def info_rows(pairs):
    rows = "".join(
        f'<div class="info-row"><span class="info-key">{k}</span>'
        f'<span class="info-val">{v}</span></div>'
        for k, v in pairs
    )
    st.markdown(rows, unsafe_allow_html=True)
