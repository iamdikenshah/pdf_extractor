"""Theme, icons and page chrome for the Streamlit UI."""

from pathlib import Path

import streamlit as st

from .registry import GROUPS, TOOLS


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
    css = (Path(__file__).parent.parent / "assets" / "styles.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)



def sidebar_nav(current):
    """Brand block plus grouped nav. Returns the selected tool."""
    count = sum(len(tools) for tools in GROUPS.values())
    with st.sidebar:
        st.markdown(
            f"""<div class="brand">
                <div class="brand-badge">{_LOGO}</div>
                <div><div class="brand-name">PDF Toolkit</div>
                <div class="brand-tag">{count} tools, one place</div></div>
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
