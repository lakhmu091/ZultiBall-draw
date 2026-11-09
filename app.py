import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Zultiball AI — Server Target", page_icon="🎯", layout="wide")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "verified_draws.csv"

st.markdown("""
<style>
.stApp {background:#080d0b;color:#e8fff1}
[data-testid="stSidebar"] {background:#101914}
h1,h2,h3 {color:#63f59a !important}
div[data-testid="stMetric"] {background:#101914;padding:14px;border:1px solid #245b3b;border-radius:12px}
</style>
""", unsafe_allow_html=True)

st.title("🎯 Zultiball AI — Server Target")
st.caption("Authorized server/API connection • current draw retrieval • JSON parsing • auto-refresh")

def get_secret(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)

with st.sidebar:
    st.header("Server connection")
    api_url = st.text_input("Authorized API URL", value=get_secret("ZULTI_API_URL"),
                            placeholder="https://your-authorized-api-endpoint")
    token = st.text_input("Bearer token (optional)", value=get_secret("ZULTI_API_TOKEN"), type="password")
    timeout = st.slider("Request timeout (seconds)", 5, 60, 20)
    st.divider()
    st.subheader("Auto-refresh")
    auto_refresh = st.toggle("Enable automatic current-draw refresh", value=False)
    refresh_seconds = st.selectbox("Refresh interval", [15, 30, 60, 120, 300], index=2)
    st.caption("Auto-refresh runs only after an authorized API URL is configured.")

def extract_numbers(payload):
    keyset = {"winning_numbers", "winningNumbers", "numbers", "draw_numbers",
              "drawNumbers", "balls", "winning"}
    candidates = []
    def walk(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k) in keyset:
                    candidates.append((path + "." + str(k), v))
                walk(v, path + "." + str(k))
        elif isinstance(obj, list):
            if obj and all(str(x).strip().isdigit() for x in obj):
                candidates.append((path, obj))
            else:
                for i, v in enumerate(obj):
                    walk(v, f"{path}[{i}]")
    walk(payload)
    for source, value in candidates:
        if isinstance(value, dict):
            value = value.get("numbers") or value.get("values") or value.get("balls")
        if isinstance(value, list):
            try:
                nums = [int(str(x).strip()) for x in value if str(x).strip().isdigit()]
                if 5 <= len(nums) <= 20 and len(nums) == len(set(nums)) and all(n > 0 for n in nums):
                    return nums, source
            except (TypeError, ValueError):
                continue
    return None, None

def request_current_draw(url, bearer, timeout_s):
    headers = {"Accept": "application/json", "User-Agent": "ZultiballAI/1.1"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    response = requests.get(url, headers=headers, timeout=timeout_s)
    response.raise_for_status()
    try:
        return response.json(), response.status_code
    except ValueError as exc:
        raise ValueError("API response was not valid JSON. Provide the server's JSON endpoint.") from exc

def load_history():
    if HISTORY_FILE.exists():
        try:
            return pd.read_csv(HISTORY_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["draw_id", "draw_date", "numbers", "source", "verified_at"])

def save_draw(draw_id, draw_date, numbers, source):
    df = load_history()
    draw_id = str(draw_id or f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    if not df.empty and draw_id in df["draw_id"].astype(str).values:
        return False, "That draw ID is already in saved history."
    row = {"draw_id": draw_id, "draw_date": str(draw_date),
           "numbers": ",".join(map(str, numbers)), "source": source,
           "verified_at": datetime.now(timezone.utc).isoformat()}
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(HISTORY_FILE, index=False)
    return True, "Saved to verified history."

# Refresh tick; the actual endpoint is still required.
if auto_refresh and api_url.strip():
    st_autorefresh(interval=refresh_seconds * 1000, key="zulti_auto_refresh")

# Fetch on initial load, manual request, or each auto-refresh tick.
should_fetch = bool(api_url.strip()) and (
    "api_payload" not in st.session_state or
    st.session_state.get("last_refresh_tick") != st.session_state.get("zulti_auto_refresh", 0)
)
manual_fetch = st.button("Fetch current draw now", type="primary")
if manual_fetch:
    should_fetch = True

if should_fetch:
    try:
        payload, status = request_current_draw(api_url.strip(), token.strip(), timeout)
        nums, source_path = extract_numbers(payload)
        st.session_state["api_payload"] = payload
        st.session_state["api_status"] = status
        st.session_state["candidate_numbers"] = nums
        st.session_state["candidate_path"] = source_path
        st.session_state["fetch_time"] = datetime.now(timezone.utc).isoformat()
        st.session_state["last_refresh_tick"] = st.session_state.get("zulti_auto_refresh", 0)
        st.session_state["fetch_error"] = None
    except Exception as exc:
        st.session_state["fetch_error"] = str(exc)

if not api_url.strip():
    st.info("Enter the authorized server/API URL in the sidebar. The app cannot identify or invent Zulti's private API endpoint.")
else:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Current draw — server response")
        if st.session_state.get("fetch_error"):
            st.error(st.session_state["fetch_error"])
        elif "api_payload" in st.session_state:
            st.caption(f"HTTP {st.session_state.get('api_status')} • fetched {st.session_state.get('fetch_time', '')}")
            candidate = st.session_state.get("candidate_numbers")
            if candidate:
                st.success("Number list parsed from the server response.")
                st.metric("Parsed number count", len(candidate))
                st.write("**Server-reported numbers:**", candidate)
                st.caption(f"JSON field: {st.session_state.get('candidate_path')}")
            else:
                st.warning("No reliable winning-number list found. Nothing was saved.")
                with st.expander("JSON response preview"):
                    st.code(json.dumps(st.session_state["api_payload"], indent=2)[:12000], language="json")
        if auto_refresh:
            st.caption(f"Auto-refresh enabled: every {refresh_seconds} seconds.")
    with right:
        st.subheader("Verification")
        candidate = st.session_state.get("candidate_numbers")
        draw_id = st.text_input("Draw ID (if supplied by API)", key="server_draw_id")
        draw_date = st.date_input("Draw date", value=datetime.now().date(), key="server_draw_date")
        st.warning("A parsed API response is server-reported, not independently verified. Confirm it against an authoritative result before saving.")
        confirmed = st.checkbox("I independently checked this draw against an official/authoritative result.")
        if st.button("Save verified current draw", disabled=not (candidate and confirmed), use_container_width=True):
            ok, message = save_draw(draw_id, draw_date.isoformat(), candidate, "server_api_user_verified")
            (st.success if ok else st.warning)(message)

st.divider()
st.subheader("Manual verified entry")
with st.form("manual_entry"):
    manual_id = st.text_input("Draw ID")
    manual_date = st.date_input("Manual draw date", value=datetime.now().date())
    manual_numbers = st.text_input("Winning numbers (comma-separated)", placeholder="3, 8, 14, 22, 31, 40")
    manual_confirm = st.checkbox("I independently verified this result.")
    submitted = st.form_submit_button("Save manual verified draw")
    if submitted:
        try:
            values = [int(x.strip()) for x in manual_numbers.split(",") if x.strip()]
            if not manual_confirm:
                st.error("Verification checkbox is required.")
            elif not (5 <= len(values) <= 20) or len(values) != len(set(values)) or any(x <= 0 for x in values):
                st.error("Enter 5–20 unique positive integers.")
            else:
                ok, message = save_draw(manual_id, manual_date.isoformat(), values, "manual_user_verified")
                (st.success if ok else st.warning)(message)
        except ValueError:
            st.error("Numbers must be comma-separated integers.")

st.divider()
st.subheader("Verified draw history & statistics")
history = load_history()
if history.empty:
    st.info("No verified draws saved yet.")
else:
    st.dataframe(history.sort_values("draw_date", ascending=False), use_container_width=True, hide_index=True)
    observed = []
    for item in history["numbers"].dropna():
        observed.extend(int(x) for x in str(item).split(",") if x.strip().isdigit())
    c1, c2, c3 = st.columns(3)
    c1.metric("Saved verified draws", len(history))
    c2.metric("Number observations", len(observed))
    c3.metric("Distinct numbers", len(set(observed)))
    if observed:
        frequencies = pd.Series(observed).value_counts().sort_values(ascending=False)
        st.write("Historical frequency (descriptive only)")
        st.bar_chart(frequencies.head(15))
    st.download_button("Download history CSV", history.to_csv(index=False).encode("utf-8"),
                       file_name="zultiball_verified_history.csv", mime="text/csv")

st.caption("No lottery prediction is guaranteed. Historical frequencies do not change the probability of a future random draw.")
