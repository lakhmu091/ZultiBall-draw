# Zultiball AI — Server Target (Streamlit)

This build targets an **authorized server/API endpoint**, not the public website HTML.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Upload the contents of this ZIP to a GitHub repository.
2. In Streamlit Community Cloud, deploy that repository.
3. Set the main file path to `app.py`.
4. Add server settings in **App → Settings → Secrets**:

```toml
ZULTI_API_URL = "https://YOUR-AUTHORIZED-API-ENDPOINT"
ZULTI_API_TOKEN = "YOUR_TOKEN_IF_REQUIRED"
```

You can also enter the API URL and optional bearer token in the app sidebar.

## Expected server response
The app accepts JSON containing a number array under common keys such as:
- `winning_numbers`
- `winningNumbers`
- `numbers`
- `draw_numbers`
- `balls`

Example:
```json
{
  "draw_id": "12345",
  "draw_date": "2026-11-09",
  "winning_numbers": [3, 8, 14, 22, 31, 40]
}
```

The app does not guess numbers from arbitrary text or HTML. A candidate is **not saved automatically**: a user must verify it before saving. If the API response shape differs, the app shows a JSON preview and reports that no verified result was saved.

## Important
- Use only an API/server endpoint you are authorized to access.
- Do not put secrets or API tokens in GitHub source files.
- Historical frequency is descriptive, not a reliable prediction of future random draws.
- This ZIP does not claim to know or discover Zulti's private API endpoint. You must supply the actual authorized endpoint and any required credentials.
