"""Collects every tool's render function into one PAGES map, keyed by the display name used in the registry."""

from . import convert, images, organise, optimise, secure, info

PAGES = {}
for _m in (convert, images, organise, optimise, secure, info):
    PAGES.update(_m.PAGES)
