# ZULTIBALL AI – Streamlit parser-fix edition

## Deploy
1. Extract this ZIP.
2. Upload the files inside to your GitHub repository root (not the ZIP itself).
3. In Streamlit Community Cloud choose the repo, branch `main`, and main file `app.py`.
4. Deploy.

## What changed
- More than one HTML parsing strategy is attempted.
- If no trustworthy winning-number cluster is found, the app does not guess or save unrelated page numbers.
- Manual verified result entry is prominent and accepts the draw's configured number count.
- Draw size and number range are configurable (Zultiball pages may show different draw sizes).
- Frequency analysis and CSV export.

## Limitation
The app cannot guarantee automatic latest-draw discovery. A documented public API/feed or stable public listing endpoint would be needed for reliable unattended discovery. Public page HTML may not include JavaScript-rendered content.
