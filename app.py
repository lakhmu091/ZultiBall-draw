import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Zultiball AI — Server Target", page_icon="🎯", layout="wide")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "verified_draws.csv"

st.markdown("""
<style>
.stApp {background: #080d0b; color: #e8fff1;}
[data-testid="stSidebar"] {background: #101914;}
h1,h2,h3 {color:#63f59a !important;}
div[data-testid="stMetric"] {background:#101914; padding:14px; border:1px solid #245b3b; border-radius:12px;}
</style>
""", unsafe_allow_html=True)

st.title("🎯 Zultiball AI — Server Target")
st.caption("Server/API-first draw retrieval • verified-only history • statistical analysis")

with st.sidebar:
    st.header("Server connection")
    default_url = st.secrets.get("ZULTI_API_URL", os.getenv("ZULTI_API_URL", ""))
    api_url = st.text_input("Draw API URL", value=default_url, placeholder="https://api.example.com/draws/latest")
    token = st.text_input(
        "Bearer token (optional)",
        value=st.secrets.get("ZULTI_API_TOKEN", os.getenv("ZULTI_API_TOKEN", "")),
        type="password",
    )
    timeout = st.slider("Request timeout (seconds)", 5, 60, 20)
    st.caption("Enter the authorized server/API endpoint, not the public website page.")

def extract_numbers(payload):
    """Extract number arrays from common JSON API response shapes."""
    candidates = []
    keys = {"winning_numbers", "winningNumbers", "numbers", "result", "results",
            "draw_numbers", "drawNumbers", "balls", "winning"}
    def walk(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys:
                    candidates.append((path + "." + str(k), v))
                walk(v, path + "." + str(k))
        elif isinstance(obj, list):
            # Preserve a direct numeric list as a candidate.
            if obj and all(isinstance(x, (int, float, str)) and str(x).strip().isdigit() for x in obj):
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
                if 5 <= len(nums) <= 20 and len(set(nums)) == len(nums):
                    return nums, source
            except (TypeError, ValueError):
                pass
    return None, None

def load_history():
    if HISTORY_FILE.exists():
        try:
            return pd.read_csv(HISTORY_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["draw_id", "draw_date", "numbers", "source", "verified_at"])

def save_verified(draw_id, draw_date, nums, source):
    df = load_history()
    row = {
        "draw_id": str(draw_id or f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        "draw_date": str(draw_date or datetime.now().date().isoformat()),
        "numbers": ",".join(map(str, nums)),
        "source": source,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    if not df.empty and row["draw_id"] in df["draw_id"].astype(str).values:
        return False, "This draw ID is already saved."
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(HISTORY_FILE, index=False)
    return True, "Verified draw saved."

def server_fetch(url, bearer, timeout_s):
    headers = {"Accept": "application/json", "User-Agent": "ZultiballAI/1.0"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    response = requests.get(url, headers=headers, timeout=timeout_s)
    response.raise_for_status()
    ctype = response.headers.get("content-type", "")
    if "json" not in ctype.lower():
        # Some APIs omit the JSON content type; accept only valid JSON.
        try:
            payload = response.json()
        except Exception as exc:
            raise ValueError("Server did not return JSON. Configure the actual API endpoint.") from exc
    else:
        payload = response.json()
    return payload, response.status_code

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("1. Fetch from server")
    if st.button("Connect & fetch latest draw", type="primary", use_container_width=True):
        if not api_url.strip():
            st.error("Enter the authorized server/API URL in the sidebar first.")
        else:
            try:
                payload, status = server_fetch(api_url.strip(), token.strip(), timeout)
                st.session_state["api_payload"] = payload
                st.session_state["api_status"] = status
                nums, path = extract_numbers(payload)
                st.session_state["candidate_numbers"] = nums
                st.session_state["candidate_path"] = path
                st.success(f"Server responded: HTTP {status}")
            except requests.RequestException as exc:
                st.error(f"Server request failed: {exc}")
            except Exception as exc:
                st.error(f"Could not read server response: {exc}")

    if "api_payload" in st.session_state:
        st.caption(f"HTTP {st.session_state.get('api_status', '')}")
        nums = st.session_state.get("candidate_numbers")
        if nums:
            st.success("Candidate list detected. Verify it against the official draw before saving.")
            st.write("Detected numbers:", nums)
            st.caption(f"JSON location: {st.session_state.get('candidate_path')}")
        else:
            st.warning("No reliable number list found in the server JSON. Nothing was saved.")
            with st.expander("Server JSON preview"):
                st.code(json.dumps(st.session_state["api_payload"], indent=2)[:12000], language="json")

with col2:
    st.subheader("2. Verify & save")
    candidate = st.session_state.get("candidate_numbers")
    draw_id = st.text_input("Draw ID (optional)", key="draw_id")
    draw_date = st.date_input("Draw date", value=datetime.now().date(), key="draw_date")
    if candidate:
        st.write("Confirm the detected numbers:")
        confirm = st.checkbox("I checked these numbers against an official/authoritative result.")
        if st.button("Save verified server draw", disabled=not confirm, use_container_width=True):
            ok, msg = save_verified(draw_id, draw_date.isoformat(), candidate, "server_api")
            (st.success if ok else st.warning)(msg)

st.divider()
st.subheader("Manual verified entry")
st.caption("Use only when you have independently confirmed the official result.")
with st.form("manual_entry"):
    m_id = st.text_input("Draw ID")
    m_date = st.date_input("Manual draw date", value=datetime.now().date())
    m_nums = st.text_input("Winning numbers (comma-separated)", placeholder="e.g. 3, 8, 14, 22, 31, 40")
    m_confirm = st.checkbox("I independently verified this result.")
    submitted = st.form_submit_button("Save manual verified draw")
    if submitted:
        try:
            values = [int(x.strip()) for x in m_nums.split(",") if x.strip()]
            if not m_confirm:
                st.error("Verification checkbox is required.")
            elif not (5 <= len(values) <= 20) or len(values) != len(set(values)) or any(x < 1 for x in values):
                st.error("Enter 5–20 unique positive integers.")
            else:
                ok, msg = save_verified(m_id, m_date.isoformat(), values, "manual_verified")
                (st.success if ok else st.warning)(msg)
        except ValueError:
            st.error("Numbers must be comma-separated integers.")

st.divider()
st.subheader("Verified draw history & analysis")
history = load_history()
if history.empty:
    st.info("No verified draws saved yet. Unverified server candidates are never added to history.")
else:
    st.dataframe(history.sort_values("draw_date", ascending=False), use_container_width=True, hide_index=True)
    all_nums = []
    for item in history["numbers"].dropna():
        all_nums.extend(int(x) for x in str(item).split(",") if x.strip().isdigit())
    freq = pd.Series(all_nums).value_counts().sort_values(ascending=False)
    a, b, c = st.columns(3)
    a.metric("Verified draws", len(history))
    b.metric("Number observations", len(all_nums))
    c.metric("Distinct numbers", len(set(all_nums)))
    if not freq.empty:
        st.write("Most frequent numbers in saved history")
        st.bar_chart(freq.head(15))
    st.download_button("Download verified history CSV", history.to_csv(index=False).encode("utf-8"),
                       file_name="zultiball_verified_history.csv", mime="text/csv")

st.caption("Statistics describe past saved draws only; they do not predict or guarantee future winning numbers.")
