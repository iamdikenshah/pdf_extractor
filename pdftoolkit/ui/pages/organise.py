"""Organise tools: merge, split, extract, delete and rotate pages."""

import streamlit as st
from ...core import pdf_ops as ops
from .. import theme as ui
from ..helpers import zip_bytes, stem, sig, upload_pdf, run_button, result_card, download, file_meta, _pages_input


def tool_merge():
    with st.container(border=True):
        ui.step(1, "Choose two or more PDFs")
        ups = st.file_uploader("PDF files", type="pdf", accept_multiple_files=True,
                               key="merge_pdfs_src")
        if not ups:
            return
        ui.step(2, "Merge order")
        ui.chips([f.name for f in ups])
        if len(ups) < 2:
            st.info("Add at least one more PDF to merge.", icon=":material/add:")
            return

        ui.step(3, "Merge")
        data = run_button(
            "merge", sig(ups),
            lambda: ops.merge_pdfs([(f.name, f.getvalue()) for f in ups]),
            "Merge PDFs", ":material/merge:",
        )

    if data:
        result_card(f"{len(ups)} files merged into one")
        with st.container(border=True):
            download(data, "merged.pdf", label="Download merged PDF", primary=True)



def tool_split():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        file_meta(up)

        ui.step(2, "Split")
        parts = run_button(
            "split", sig(up, pw),
            lambda: ops.split_to_pages(up.getvalue(), password=pw),
            "Split into single pages", ":material/content_cut:",
        )

    if parts:
        result_card(f"Split into {len(parts)} files")
        with st.container(border=True):
            download(zip_bytes(parts), f"{stem(up.name)}_split.zip", "application/zip",
                     f"Download all {len(parts)} PDFs (ZIP)", primary=True)



def tool_extract():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        ui.step(2, "Pages to keep")
        spec = _pages_input(up, pw, "Leave empty to keep every page.")
        if spec is None:
            return

        ui.step(3, "Extract")
        data = run_button(
            "extract", sig(up, spec, pw),
            lambda: ops.extract_pages(up.getvalue(), spec, password=pw),
            "Extract pages", ":material/file_copy:",
        )

    if data:
        result_card("Pages extracted")
        with st.container(border=True):
            download(data, f"{stem(up.name)}_extracted.pdf", label="Download PDF", primary=True)



def tool_delete():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        ui.step(2, "Pages to remove")
        spec = _pages_input(up, pw, "These pages are deleted. Everything else is kept.")
        if spec is None:
            return
        if not spec.strip():
            st.info("Enter which pages to delete.", icon=":material/edit:")
            return

        ui.step(3, "Delete")
        data = run_button(
            "delete", sig(up, spec, pw),
            lambda: ops.delete_pages(up.getvalue(), spec, password=pw),
            "Delete pages", ":material/delete:",
        )

    if data:
        result_card("Pages removed")
        with st.container(border=True):
            download(data, f"{stem(up.name)}_edited.pdf", label="Download PDF", primary=True)



def tool_rotate():
    with st.container(border=True):
        ui.step(1, "Choose your PDF")
        up, pw = upload_pdf()
        if not up:
            return
        ui.step(2, "Pages to rotate")
        spec = _pages_input(up, pw, "Leave empty to rotate every page.")
        if spec is None:
            return

        ui.step(3, "Direction")
        angle = st.radio("Rotate by", [90, 180, 270], horizontal=True,
                         format_func=lambda a: f"{a}°", label_visibility="collapsed")

        data = run_button(
            "rotate", sig(up, spec, angle, pw),
            lambda: ops.rotate_pages(up.getvalue(), spec, angle, password=pw),
            "Rotate pages", ":material/rotate_right:",
        )

    if data:
        result_card("Pages rotated")
        with st.container(border=True):
            download(data, f"{stem(up.name)}_rotated.pdf", label="Download PDF", primary=True)



PAGES = {
    "Merge PDFs": tool_merge,
    "Split PDF": tool_split,
    "Extract pages": tool_extract,
    "Delete pages": tool_delete,
    "Rotate pages": tool_rotate,
}
