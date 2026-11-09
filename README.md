# Zultiball AI — Live Draw Monitor

## Features
- Authorized JSON API fetch with configurable JSON paths.
- Public webpage fallback using CSS selectors, JSON-LD, and a cautious text candidate scan.
- Candidate confirmation before public-page results are saved.
- Manual verified draw entry.
- Automatic refresh and configurable fetch interval.
- Verified history, frequency charts, timeline, and CSV export.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Extract this ZIP.
2. Upload `app.py`, `requirements.txt`, and `README.md` to GitHub.
3. Create a Streamlit Community Cloud app using `app.py`.
4. Enter an authorized API URL or a publicly accessible results page in the sidebar.
5. For JSON API mode, set paths such as `draw.id`, `draw.date`, and `draw.numbers`.
6. For public page mode, set CSS selector for the numbers element if known (e.g. `.winning-numbers`).
7. Verify a detected candidate before saving.

## Example JSON
```json
{
  "draw": {
    "id": "DRAW-1001",
    "date": "2026-11-10",
    "numbers": [3, 8, 14, 22, 31, 40]
  }
}
```

## Important limitations
- The public-page parser uses HTTP HTML and cannot run client-side JavaScript.
- It cannot bypass authentication, CAPTCHA, access controls, or private APIs.
- A candidate from heuristic extraction is not automatically treated as verified.
- Streamlit Community Cloud local files may not persist through restarts/redeployments. Use a database for durable production storage.
- Frequency charts describe historical observations; they do not predict or guarantee future results.
- Do not publish API keys in GitHub. Use Streamlit secrets or a secure server-side secret store for production.
