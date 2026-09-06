"""Image tools: convert, resize, compress, rotate/flip, background colour."""

import streamlit as st
from ...core import image_ops as imgops
from .. import theme as ui
from ..helpers import human_size, stem, sig, result_card, _image_uploads, _deliver_images, _run_over_images


def tool_img_convert():
    with st.container(border=True):
        ui.step(1, "Choose your images")
        ups = _image_uploads()
        ui.step(2, "Output format")
        c1, c2 = st.columns(2)
        fmt = c1.selectbox("Convert to", list(imgops.OUTPUT_FORMATS))
        quality = c2.slider("Quality", 40, 100, imgops.DEFAULT_QUALITY,
                            help="Used by JPG and WEBP.")
        bg = None
        if imgops.OUTPUT_FORMATS[fmt][0] in imgops.OPAQUE_FORMATS:
            bg = st.color_picker("Background for transparent areas", "#FFFFFF",
                                 help=f"{fmt} cannot store transparency.")
        if not ups:
            return
        ui.step(3, "Convert")
        results = _run_over_images(
            ups, lambda b, n: imgops.convert(b, fmt, quality, bg or "#FFFFFF"),
            "img_convert", sig(ups, fmt, quality, bg), f"Convert to {fmt}",
            ":material/swap_horiz:")
    if results:
        result_card(f"{len(results)} image{'s' if len(results) != 1 else ''} converted")
        with st.container(border=True):
            _deliver_images(results, "image", stem(ups[0].name))



def tool_img_resize():
    with st.container(border=True):
        ui.step(1, "Choose your images")
        ups = _image_uploads()
        ui.step(2, "New size")
        mode = st.radio("Resize by", ["Percentage", "Dimensions"], horizontal=True)
        percent = width = height = None
        keep = True
        if mode == "Percentage":
            percent = st.slider("Scale", 5, 400, 50, format="%d%%")
        else:
            c1, c2 = st.columns(2)
            width = c1.number_input("Width (px)", 0, 20000, 800) or None
            height = c2.number_input("Height (px)", 0, 20000, 0) or None
            keep = st.checkbox("Keep aspect ratio", True)
            if not width and not height:
                st.info("Enter a width, a height, or both.", icon=":material/straighten:")
        if not ups:
            return
        ui.step(3, "Resize")
        results = _run_over_images(
            ups,
            lambda b, n: imgops.resize(b, width, height, percent, keep)[:2],
            "img_resize", sig(ups, mode, percent, width, height, keep),
            "Resize", ":material/photo_size_select_large:")
    if results:
        result_card(f"{len(results)} image{'s' if len(results) != 1 else ''} resized")
        with st.container(border=True):
            _deliver_images(results, "image", stem(ups[0].name))



def tool_img_compress():
    with st.container(border=True):
        ui.step(1, "Choose your images")
        ups = _image_uploads()
        ui.step(2, "Compression")
        quality = st.slider("Quality", 10, 95, 70,
                            help="Lower means smaller files and more visible loss.")
        as_webp = st.checkbox("Save as WEBP (usually smaller than JPG)")
        if not ups:
            return
        ui.step(3, "Compress")
        fmt = "WEBP" if as_webp else None
        results = _run_over_images(
            ups, lambda b, n: imgops.compress(b, quality, fmt),
            "img_compress", sig(ups, quality, as_webp), "Compress",
            ":material/compress:")
    if results:
        before = sum(u.size for u in ups)
        after = sum(len(d) for _, d in results)
        result_card("Compression finished")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            c1.metric("Before", human_size(before))
            c2.metric("After", human_size(after),
                      f"{(after - before) / before * 100:.0f}%", delta_color="inverse")
            st.markdown("")
            _deliver_images(results, "image", stem(ups[0].name))



def tool_img_transform():
    with st.container(border=True):
        ui.step(1, "Choose your images")
        ups = _image_uploads()
        ui.step(2, "Turn or mirror")
        angle = st.radio("Rotate", [0, 90, 180, 270], horizontal=True,
                         format_func=lambda a: "None" if a == 0 else f"{a}°")
        flip = st.radio("Flip", ["None", "Horizontal", "Vertical"], horizontal=True)
        if not ups:
            return
        if angle == 0 and flip == "None":
            st.info("Pick a rotation or a flip.", icon=":material/flip:")
            return
        ui.step(3, "Apply")
        flip_arg = None if flip == "None" else flip.lower()
        results = _run_over_images(
            ups, lambda b, n: imgops.transform(b, angle, flip_arg),
            "img_transform", sig(ups, angle, flip), "Apply",
            ":material/flip:")
    if results:
        result_card("Done")
        with st.container(border=True):
            _deliver_images(results, "image", stem(ups[0].name))



def tool_img_background():
    with st.container(border=True):
        ui.step(1, "Choose your images")
        st.caption("For images with transparent areas, such as a PNG logo or a "
                   "signature. It fills the transparency; it does not remove a "
                   "photographic background.")
        ups = _image_uploads()
        ui.step(2, "Background")
        c1, c2 = st.columns(2)
        color = c1.color_picker("Colour", "#FFFFFF")
        fmt = c2.selectbox("Save as", ["PNG", "JPG", "WEBP"])
        if not ups:
            return
        ui.step(3, "Fill background")
        results = _run_over_images(
            ups, lambda b, n: imgops.set_background(b, color, fmt),
            "img_bg", sig(ups, color, fmt), "Fill background",
            ":material/format_color_fill:")
    if results:
        result_card(f"{len(results)} image{'s' if len(results) != 1 else ''} done")
        with st.container(border=True):
            _deliver_images(results, "image", stem(ups[0].name))



PAGES = {
    "Convert image": tool_img_convert,
    "Resize image": tool_img_resize,
    "Compress image": tool_img_compress,
    "Rotate / Flip image": tool_img_transform,
    "Background colour": tool_img_background,
}
