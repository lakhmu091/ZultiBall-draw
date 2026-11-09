import json, re
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Zultiball AI — Live Draw Monitor", page_icon="🎯", layout="wide")
DB = Path("verified_draws.csv")
TIMEOUT = 20
UA = "Mozilla/5.0 (compatible; ZultiballDrawMonitor/1.0)"

st.title("🎯 Zultiball AI — Live Draw Monitor")
st.caption("Authorized API + public-page fallback + verified history + statistics")

def read_db():
    if DB.exists():
        try:
            df = pd.read_csv(DB)
            required = ["draw_id", "draw_date", "numbers", "verified", "source"]
            if all(c in df.columns for c in required):
                return df
        except Exception:
            pass
    return pd.DataFrame(columns=["draw_id", "draw_date", "numbers", "verified", "source"])

def write_db(df):
    df.to_csv(DB, index=False)

def parse_numbers(value):
    if isinstance(value, str):
        raw = re.findall(r"(?<!\d)\d+(?!\d)", value)
    elif isinstance(value, list):
        raw = value
    else:
        return None
    try:
        nums = [int(x) for x in raw]
    except (TypeError, ValueError):
        return None
    if not 5 <= len(nums) <= 20 or any(n <= 0 for n in nums) or len(set(nums)) != len(nums):
        return None
    return nums

def get_path(obj, path):
    cur = obj
    for key in filter(None, path.strip().split(".")):
        if isinstance(cur, list) and key.isdigit() and int(key) < len(cur):
            cur = cur[int(key)]
        elif isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur

def save_draw(draw_id, draw_date, nums, source):
    df = read_db()
    row = {"draw_id": str(draw_id), "draw_date": str(draw_date),
           "numbers": ",".join(map(str, nums)), "verified": True, "source": source}
    if not df.empty:
        df = df[df.draw_id.astype(str) != str(draw_id)]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    write_db(df)

def request_page(url, headers):
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r

def parse_json_api(payload, id_path, date_path, nums_path):
    draw_id = get_path(payload, id_path)
    draw_date = get_path(payload, date_path)
    nums = parse_numbers(get_path(payload, nums_path))
    if draw_id is None or nums is None:
        raise ValueError("Configured JSON paths did not return a draw ID and 5–20 unique positive numbers.")
    return str(draw_id), str(draw_date or date.today().isoformat()), nums

def parse_public_page(html, id_selector, date_selector, numbers_selector):
    soup = BeautifulSoup(html, "html.parser")
    # Prefer configured CSS selectors.
    if numbers_selector.strip():
        node = soup.select_one(numbers_selector)
        if node:
            nums = parse_numbers(node.get("content") or node.get_text(" ", strip=True))
            if nums:
                id_node = soup.select_one(id_selector) if id_selector.strip() else None
                date_node = soup.select_one(date_selector) if date_selector.strip() else None
                draw_id = (id_node.get("content") or id_node.get_text(" ", strip=True)) if id_node else "public-page-" + date.today().isoformat()
                draw_date = (date_node.get("content") or date_node.get_text(" ", strip=True)) if date_node else date.today().isoformat()
                return str(draw_id), str(draw_date), nums, "CSS selector"

    # Try structured JSON-LD blocks. This is heuristic, so the user must confirm.
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or tag.get_text())
            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                if isinstance(item, dict):
                    for key in ("winningNumbers", "numbers", "results", "number"):
                        nums = parse_numbers(item.get(key))
                        if nums:
                            return str(item.get("identifier") or item.get("name") or "public-jsonld"), str(item.get("datePublished") or date.today().isoformat()), nums, "JSON-LD"
        except Exception:
            continue

    # Last-resort candidate scan: report candidate only; never auto-save.
    text = soup.get_text(" ", strip=True)
    matches = re.findall(r"(?<!\d)(?:\d{1,3}\s*[,|]\s*){4,19}\d{1,3}(?!\d)", text)
    for candidate in matches:
        nums = parse_numbers(candidate)
        if nums:
            return "public-candidate-" + date.today().isoformat(), date.today().isoformat(), nums, "text heuristic candidate"
    raise ValueError("No recognizable public winning-number list found. The page may be client-rendered, protected, or use a different structure.")

with st.sidebar:
    st.header("1) Data source")
    mode = st.radio("Connection mode", ["Authorized JSON API", "Public webpage fallback", "Manual only"])
    url = st.text_input("API / public page URL", placeholder="https://your-authorized-server.example/api/draw")
    headers_raw = st.text_area("Request headers (JSON)", '{"User-Agent":"Mozilla/5.0"}', height=80)
    refresh = st.number_input("Auto-refresh (seconds)", 0, 3600, 60, 5)
    auto_fetch = st.checkbox("Fetch automatically on each refresh", value=True)
    st.divider()
    st.header("2) API JSON mapping")
    id_path = st.text_input("Draw ID path", "draw.id")
    date_path = st.text_input("Draw date path", "draw.date")
    nums_path = st.text_input("Numbers path", "draw.numbers")
    st.divider()
    st.header("3) Public page CSS selectors")
    id_css = st.text_input("Draw ID selector (optional)", "")
    date_css = st.text_input("Draw date selector (optional)", "")
    nums_css = st.text_input("Winning numbers selector", "")
    st.caption("Example selector: .winning-numbers or #result-numbers")

if refresh > 0:
    st_autorefresh(interval=int(refresh * 1000), key="zulti_refresh")

def run_fetch():
    if not url.strip():
        st.warning("Enter a URL in the sidebar.")
        return
    try:
        headers = json.loads(headers_raw or "{}")
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a JSON object.")
        response = request_page(url.strip(), headers)
        content_type = response.headers.get("content-type", "").lower()
        if mode == "Authorized JSON API" or "json" in content_type:
            payload = response.json()
            did, ddate, nums = parse_json_api(payload, id_path, date_path, nums_path)
            save_draw(did, ddate, nums, "Authorized JSON API")
            st.success(f"Fetched and saved draw {did}: {', '.join(map(str, nums))}")
        else:
            did, ddate, nums, method_used = parse_public_page(response.text, id_css, date_css, nums_css)
            st.session_state["candidate"] = {"id": did, "date": ddate, "nums": nums, "method": method_used}
            st.info(f"Found a candidate using {method_used}: {', '.join(map(str, nums))}. Confirm it below before saving.")
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
    except (ValueError, json.JSONDecodeError) as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Could not process source: {e}")

col_a, col_b = st.columns([1, 3])
with col_a:
    if st.button("🔄 Fetch now", type="primary", use_container_width=True):
        run_fetch()
with col_b:
    st.caption("Auto-fetch runs on refresh only when a URL is entered and automatic fetching is enabled.")
if refresh > 0 and auto_fetch and url.strip() and mode != "Manual only":
    # Avoid a request on the initial render if no prior refresh cycle has elapsed.
    if st.session_state.get("_auto_fetch_ready", False):
        run_fetch()
    st.session_state["_auto_fetch_ready"] = True

if "candidate" in st.session_state:
    c = st.session_state["candidate"]
    st.subheader("Public-page candidate — verification required")
    st.write(f"**Candidate draw:** {c['id']}  |  **Date:** {c['date']}")
    st.write("**Candidate numbers:** " + ", ".join(map(str, c["nums"])))
    confirm = st.checkbox("I checked this candidate against the official result and confirm it is correct.", key="candidate_confirm")
    if st.button("Save confirmed candidate"):
        if confirm:
            save_draw(c["id"], c["date"], c["nums"], "Public page — user confirmed")
            del st.session_state["candidate"]
            st.success("Confirmed draw saved.")
            st.rerun()
        else:
            st.error("Please verify the candidate before saving.")

st.divider()
st.subheader("Manual verified entry")
with st.form("manual"):
    a, b = st.columns(2)
    manual_id = a.text_input("Draw ID")
    manual_date = b.date_input("Draw date", value=date.today())
    manual_nums = st.text_input("Winning numbers (comma-separated)", "3, 8, 14, 22, 31, 40")
    manual_confirm = st.checkbox("I independently verified this result.")
    submit = st.form_submit_button("Save manual draw")
    if submit:
        nums = parse_numbers(manual_nums)
        if not manual_id.strip():
            st.error("Draw ID is required.")
        elif nums is None:
            st.error("Enter 5–20 unique positive integers.")
        elif not manual_confirm:
            st.error("Confirm independent verification before saving.")
        else:
            save_draw(manual_id, manual_date.isoformat(), nums, "Manual verified entry")
            st.success("Verified draw saved.")
            st.rerun()

st.divider()
st.subheader("Verified draw history & statistics")
hist = read_db()
if hist.empty:
    st.info("No verified draws saved yet.")
else:
    hist = hist[hist["verified"].astype(str).str.lower().isin(["true", "1"])]
    st.dataframe(hist.sort_values("draw_date", ascending=False), use_container_width=True, hide_index=True)
    flat = []
    for cell in hist["numbers"].dropna():
        flat.extend(parse_numbers(str(cell)) or [])
    if flat:
        freq = pd.Series(flat).value_counts().sort_index().rename_axis("Number").reset_index(name="Frequency")
        left, right = st.columns(2)
        with left:
            st.plotly_chart(px.bar(freq, x="Number", y="Frequency", title="Verified number frequency"), use_container_width=True)
        with right:
            st.plotly_chart(px.histogram(freq, x="Frequency", title="Frequency distribution"), use_container_width=True)
    timeline = hist.groupby("draw_date").size().reset_index(name="Draws")
    st.plotly_chart(px.line(timeline, x="draw_date", y="Draws", markers=True, title="Verified draws over time"), use_container_width=True)
    st.download_button("Download history CSV", hist.to_csv(index=False).encode(), "verified_draws.csv", "text/csv")

st.warning("This tool cannot guarantee predictions. Public-page extraction is heuristic and requires confirmation. It cannot execute browser JavaScript, defeat CAPTCHA, bypass logins, or access private endpoints without authorization.")
