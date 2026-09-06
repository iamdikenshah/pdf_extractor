"""Image operations. Pure functions on bytes, using Pillow. No UI code.

Everything here uses only Pillow, which ships in both the local install and the
browser (Pyodide) build, so every image tool works in both. HEIC is deliberately
absent: decoding it needs libheif, which has no WebAssembly build, so it could
not run on the hosted site.
"""

import io

from PIL import Image, ImageOps

# HEIC/HEIF (iPhone photos) decode through pillow-heif, which registers itself
# into Pillow. It is available both locally and in the browser build (Pyodide
# ships it), but we still guard the import so the rest keeps working if it is
# ever missing, in which case HEIC is simply not offered.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except Exception:  # pragma: no cover - only hit when the package is absent
    HEIC_SUPPORTED = False

# What we accept in, and what we can write out.
INPUT_TYPES = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"]
if HEIC_SUPPORTED:
    INPUT_TYPES += ["heic", "heif"]
OUTPUT_FORMATS = {
    "JPG": ("JPEG", "jpg"),
    "PNG": ("PNG", "png"),
    "WEBP": ("WEBP", "webp"),
    "BMP": ("BMP", "bmp"),
    "TIFF": ("TIFF", "tiff"),
    "GIF": ("GIF", "gif"),
}
# Formats that cannot store transparency, so they need a background colour.
OPAQUE_FORMATS = {"JPEG", "BMP"}
DEFAULT_QUALITY = 85


def _hex_to_rgb(value):
    """'#4F46E5' -> (79, 70, 229)."""
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


# ISO base-media "ftyp" brands used by HEIF/HEIC files.
_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis",
                b"hevm", b"hevs", b"mif1", b"msf1"}


def _looks_like_heif(data):
    return len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in _HEIF_BRANDS


def _load(image_bytes):
    if HEIC_SUPPORTED and _looks_like_heif(image_bytes):
        # Decode HEIC/HEIF through pillow-heif directly rather than via Pillow's
        # plugin. iPhone photos are often 10-bit HDR, which the plugin path can
        # fail to read ("cannot identify image file"); convert_hdr_to_8bit makes
        # them into ordinary 8-bit images.
        im = pillow_heif.open_heif(image_bytes, convert_hdr_to_8bit=True).to_pillow()
        src_format = "HEIF"
    else:
        im = Image.open(io.BytesIO(image_bytes))
        im.load()
        src_format = im.format
    # honour EXIF orientation so phone photos are not sideways
    im = ImageOps.exif_transpose(im)
    im.format = src_format  # exif_transpose returns a copy that drops this
    return im


def _flatten(im, background="#FFFFFF"):
    """Composite an image with transparency onto a solid colour."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        base = Image.new("RGBA", im.size, _hex_to_rgb(background) + (255,))
        base.alpha_composite(im.convert("RGBA"))
        return base.convert("RGB")
    return im.convert("RGB")


def _save(im, pil_format, quality, background="#FFFFFF"):
    if pil_format in OPAQUE_FORMATS:
        im = _flatten(im, background)
    elif pil_format in ("PNG", "WEBP") and im.mode not in ("RGBA", "RGB", "P", "L"):
        im = im.convert("RGBA")

    buf = io.BytesIO()
    params = {}
    if pil_format in ("JPEG", "WEBP"):
        params["quality"] = quality
    if pil_format == "JPEG":
        params["optimize"] = True
    im.save(buf, pil_format, **params)
    return buf.getvalue()


def _resolve_format(out_format):
    try:
        return OUTPUT_FORMATS[out_format]
    except KeyError:
        raise ValueError(f"Unsupported output format: {out_format}") from None


def convert(image_bytes, out_format="PNG", quality=DEFAULT_QUALITY, background="#FFFFFF"):
    """Change an image's format. Returns (jpg/png/... bytes, extension)."""
    pil_format, ext = _resolve_format(out_format)
    return _save(_load(image_bytes), pil_format, quality, background), ext


def resize(image_bytes, width=None, height=None, percent=None, keep_aspect=True,
           out_format=None, quality=DEFAULT_QUALITY, background="#FFFFFF"):
    """Resize by target dimensions or by a percentage of the original."""
    im = _load(image_bytes)
    w0, h0 = im.size

    if percent:
        w, h = max(1, round(w0 * percent / 100)), max(1, round(h0 * percent / 100))
    elif width and height and not keep_aspect:
        w, h = width, height
    elif width or height:
        if width and height:
            scale = min(width / w0, height / h0)      # fit inside the box
        else:
            scale = (width / w0) if width else (height / h0)
        w, h = max(1, round(w0 * scale)), max(1, round(h0 * scale))
    else:
        raise ValueError("Give a width, a height, or a percentage.")

    resized = im.resize((w, h), Image.LANCZOS)
    if out_format:
        pil_format, ext = _resolve_format(out_format)
    else:
        pil_format = im.format or "PNG"
        ext = OUTPUT_FORMATS.get(pil_format if pil_format != "JPEG" else "JPG",
                                 (pil_format, pil_format.lower()))[1]
    return _save(resized, pil_format, quality, background), ext, (w, h)


def compress(image_bytes, quality=70, out_format=None, background="#FFFFFF"):
    """Re-encode at a lower quality to shrink the file."""
    im = _load(image_bytes)
    if out_format:
        pil_format, ext = _resolve_format(out_format)
    else:
        # keep the type if it is lossy-capable, otherwise default to JPG
        src = (im.format or "").upper()
        pil_format, ext = ("WEBP", "webp") if src == "WEBP" else ("JPEG", "jpg")
    return _save(im, pil_format, quality, background), ext


def transform(image_bytes, rotate=0, flip=None, out_format=None,
              quality=DEFAULT_QUALITY, background="#FFFFFF"):
    """Rotate by 0/90/180/270 degrees and optionally mirror the image."""
    im = _load(image_bytes)
    if rotate:
        if rotate % 90:
            raise ValueError("Rotation must be a multiple of 90 degrees.")
        im = im.rotate(-rotate, expand=True)   # negative = clockwise
    if flip == "horizontal":
        im = ImageOps.mirror(im)
    elif flip == "vertical":
        im = ImageOps.flip(im)

    if out_format:
        pil_format, ext = _resolve_format(out_format)
    else:
        pil_format = im.format or "PNG"
        ext = OUTPUT_FORMATS.get("JPG" if pil_format == "JPEG" else pil_format,
                                 (pil_format, pil_format.lower()))[1]
    return _save(im, pil_format, quality, background), ext


def set_background(image_bytes, color="#FFFFFF", out_format="PNG",
                   quality=DEFAULT_QUALITY):
    """Replace transparency with a solid colour.

    Useful for logos, signatures and product shots saved on a transparent
    background. It does not detect or remove a photographic background -- that
    needs an ML model this app deliberately does not carry.
    """
    im = _load(image_bytes)
    if im.mode not in ("RGBA", "LA") and not (im.mode == "P" and "transparency" in im.info):
        raise ValueError(
            "This image has no transparent areas to fill. Background colour only "
            "applies to images with transparency, such as a PNG logo."
        )
    flat = _flatten(im, color)
    pil_format, ext = _resolve_format(out_format)
    return _save(flat, pil_format, quality, color), ext


def info(image_bytes):
    """Basic facts for display."""
    im = _load(image_bytes)
    return {
        "Format": im.format or "-",
        "Size": f"{im.size[0]} x {im.size[1]} px",
        "Mode": im.mode,
        "Transparency": "Yes" if im.mode in ("RGBA", "LA")
        or (im.mode == "P" and "transparency" in im.info) else "No",
    }
