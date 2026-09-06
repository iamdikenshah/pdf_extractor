"""The tools the app offers: their metadata and their grouping.

This is the one place that defines what appears in the menu. Page render
functions are collected separately in ui/pages/ and matched by name.
"""

# Tool -> (Material icon, one-line description)
TOOLS = {
    "PDF to JPG": ("image", "Render every page as a high quality JPG image."),
    "Images to PDF": ("picture_as_pdf", "Combine images into a single PDF, one per page."),
    "Extract text": ("notes", "Pull the text out of a PDF and save it as a file."),
    # "Edit PDF" and "Apply to all pages" are temporarily removed from the menu;
    # their code is kept in editor.py and app.py so they can be re-added later.
    "Convert image": ("swap_horiz", "Change an image between HEIC, PNG, JPG, WEBP and more."),
    "Resize image": ("photo_size_select_large", "Scale images by size or percentage."),
    "Compress image": ("compress", "Shrink an image's file size."),
    "Rotate / Flip image": ("flip", "Turn or mirror an image."),
    "Background colour": ("format_color_fill",
                          "Fill the transparent areas of a PNG with a solid colour."),
    "Merge PDFs": ("merge", "Join several PDFs into one, in the order you choose."),
    "Split PDF": ("content_cut", "Break a PDF into one separate file per page."),
    "Extract pages": ("file_copy", "Keep only the pages you select."),
    "Delete pages": ("delete", "Remove the pages you no longer need."),
    "Rotate pages": ("rotate_right", "Turn pages 90, 180 or 270 degrees."),
    "Compress PDF": ("compress", "Shrink the file size of a PDF."),
    "Protect / Unlock": ("lock", "Add a password, or remove one you know."),
    "PDF info": ("info", "Inspect a document without changing it."),
}


# Sidebar grouping and order
GROUPS = {
    "Convert": ["PDF to JPG", "Images to PDF", "Extract text"],
    "Images": ["Convert image", "Resize image", "Compress image",
               "Rotate / Flip image", "Background colour"],
    "Organise": ["Merge PDFs", "Split PDF", "Extract pages", "Delete pages", "Rotate pages"],
    "Optimise": ["Compress PDF"],
    "Secure": ["Protect / Unlock"],
    "Inspect": ["PDF info"],
}
