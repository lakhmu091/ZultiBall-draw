# ZULTIBALL AI – Streamlit Edition

A Python/Streamlit web app for recording and statistically analyzing Zultiball draw history.

## Deploy on Streamlit Community Cloud
1. Create a GitHub repository, for example `zultiball-ai-streamlit`.
2. Extract this ZIP on your device.
3. Upload **all files inside this folder** to the repository root. Do not upload only the ZIP.
4. Open https://share.streamlit.io/ and sign in with GitHub.
5. Select **Create app**.
6. Choose your repository, branch `main`, and main file path `app.py`.
7. Click **Deploy**.

## Features
- Dark black + neon-green UI
- Configurable number range and numbers-per-draw
- Public Zulti draw page fetch attempt
- Manual entry of verified draw results
- SQLite draw-history storage
- Hot/cold frequency tables and chart
- Frequency-ranked example combinations
- CSV export

## Important limitations
- The result-page reader only works if the public HTML contains a readable `Winning numbers` section. If the page is JavaScript-rendered or its layout changes, enter the verified result manually.
- This app does not have a verified official Zulti API or feed for automatic discovery of newly published draws. It cannot promise fully automatic latest-draw discovery.
- Streamlit Community Cloud's local filesystem is not guaranteed durable. Use a hosted database for persistent records in production.
- This is not a hack or MOD. It only attempts to read a public page and analyze saved data.
- Statistical patterns cannot guarantee future lottery outcomes.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
