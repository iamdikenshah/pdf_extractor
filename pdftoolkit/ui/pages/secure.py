"""Secure: add or remove a password, or strip restrictions."""

import streamlit as st
from ...core import pdf_ops as ops
from .. import theme as ui
from ..helpers import stem, sig, run_button, result_card, download, file_meta


def tool_password():
    with st.container(border=True):
        ui.step(1, "What do you want to do?")
        action = st.radio(
            "Action",
            ["Add a password", "Remove a password", "Remove restrictions (no password)"],
            label_visibility="collapsed",
        )
        ui.step(2, "Choose your PDF")
        up = st.file_uploader("PDF file", type="pdf")
        if not up:
            return
        file_meta(up)

        if action == "Add a password":
            ui.step(3, "Set the password")
            new_pw = st.text_input("New password", type="password",
                                   placeholder="Choose a strong password")
            data = run_button(
                "protect", sig(up, new_pw),
                lambda: ops.add_password(up.getvalue(), new_pw),
                "Protect PDF", ":material/lock:",
            )
            name, note = f"{stem(up.name)}_protected.pdf", "Password added (AES-256)"
        elif action == "Remove a password":
            ui.step(3, "Enter the current password")
            pw = st.text_input("Current password", type="password")
            data = run_button(
                "unlock", sig(up, pw),
                lambda: ops.remove_password(up.getvalue(), pw),
                "Unlock PDF", ":material/lock_open:",
            )
            name, note = f"{stem(up.name)}_unlocked.pdf", "Password removed"
        else:
            ui.step(3, "Remove the restrictions")
            st.caption(
                "For PDFs that open without a password but block printing, copying "
                "or editing. It cannot open a PDF that needs a password just to view."
            )
            data = run_button(
                "unrestrict", sig(up),
                lambda: ops.remove_restrictions(up.getvalue()),
                "Remove restrictions", ":material/lock_open_right:",
            )
            name, note = f"{stem(up.name)}_unrestricted.pdf", "Restrictions removed"

    if data:
        result_card(note)
        with st.container(border=True):
            download(data, name, label="Download PDF", primary=True)



PAGES = {
    "Protect / Unlock": tool_password,
}
