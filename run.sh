#!/bin/bash
# Launch the PDF to JPG web app and open it in the browser.

cd "$(dirname "$0")" || exit 1

if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing dependencies..."
    python3 -m pip install -r requirements.txt || exit 1
fi

echo "Starting PDF to JPG... (press Ctrl+C to stop)"
exec python3 -m streamlit run app.py "$@"
