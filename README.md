# Zultiball AI — Server Target

## Features
- Connects to an authorized JSON API endpoint (not website HTML).
- Fetches the current server response on app load and on demand.
- Parses common JSON number fields: `winning_numbers`, `winningNumbers`, `numbers`, `draw_numbers`, `drawNumbers`, `balls`, `winning`.
- Optional auto-refresh at 15, 30, 60, 120, or 300 seconds.
- Shows JSON preview when no reliable number list is detected.
- Saves results only after explicit user confirmation against an authoritative result.
- Stores verified history locally in `data/verified_draws.csv` and provides CSV export.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud
Upload this ZIP's contents to GitHub and deploy `app.py`. Add secrets under App Settings → Secrets:
```toml
ZULTI_API_URL = "https://YOUR-AUTHORIZED-API-ENDPOINT"
ZULTI_API_TOKEN = "OPTIONAL_BEARER_TOKEN"
```
The URL must be the actual authorized server/API endpoint that returns JSON. This project does not guess or claim to know Zulti's private endpoint. If the server returns a different JSON shape, use the JSON preview to adapt the parser.

## Verification note
Parsing a number array proves only that the API returned those values. It does not prove that they are official winning numbers. The app therefore requires the user to independently verify a result before saving it as verified.
