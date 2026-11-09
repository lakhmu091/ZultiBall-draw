import re
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

APP_TITLE = "ZULTIBALL AI"
DB_PATH = "zultiball.db"
DEFAULT_MIN = 1
DEFAULT_MAX = 49

st.set_page_config(page_title=APP_TITLE, page_icon="🎯", layout="wide")

st.markdown("""
<style>
.stApp { background: #080d0b; color: #e8f5ec; }
[data-testid="stSidebar"] { background: #0c1710; }
h1, h2, h3 { color: #54ff85 !important; }
div.stButton > button {
  background: #10251a; color: #54ff85; border: 1px solid #287c42;
  border-radius: 10px; font-weight: 700;
}
div.stButton > button:hover { background: #173a25; color: white; border-color: #54ff85; }
div[data-testid="stMetric"] {
  background: #10251a; border: 1px solid #245536; padding: 12px; border-radius: 12px;
}
div[data-testid="stDataFrame"] { border: 1px solid #245536; }
.small-note { color: #a0b6a7; font-size: 0.88rem; }
.number-pill {
 display:inline-block; background:#10251a; color:#54ff85; border:1px solid #287c42;
 padding:9px 13px; margin:4px; border-radius:10px; font-size:1.1rem; font-weight:700;
}
</style>
""", unsafe_allow_html=True)


def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("""
        CREATE TABLE IF NOT EXISTS draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_date TEXT,
            source_url TEXT,
            numbers TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def validate_numbers(values, min_n, max_n):
    nums = []
    for value in values:
        try:
            n = int(value)
        except (TypeError, ValueError):
            continue
        if min_n <= n <= max_n and n not in nums:
            nums.append(n)
    return sorted(nums)


def save_draw(numbers, draw_date="", source_url=""):
    con = connect()
    con.execute(
        "INSERT INTO draws(draw_date, source_url, numbers, created_at) VALUES (?, ?, ?, ?)",
        (draw_date, source_url, ",".join(map(str, numbers)),
         datetime.now(timezone.utc).isoformat())
    )
    con.commit()
    con.close()


def load_draws():
    con = connect()
    rows = con.execute(
        "SELECT id, draw_date, source_url, numbers, created_at FROM draws ORDER BY id DESC"
    ).fetchall()
    con.close()
    result = []
    for row in rows:
        result.append({
            "id": row[0], "draw_date": row[1], "source_url": row[2],
            "numbers": [int(x) for x in row[3].split(",") if x],
            "created_at": row[4]
        })
    return result


def fetch_public_draw_page(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"zulti.com", "www.zulti.com"}:
        raise ValueError("Only public HTTPS pages on zulti.com are accepted.")
    if not parsed.path.startswith("/draws/"):
        raise ValueError("Please enter a public Zulti draw-page URL beginning with /draws/.")

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ZultiballAnalysis/1.0)"}
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    marker = re.search(r"winning\s+numbers", text, flags=re.I)
    if not marker:
        raise RuntimeError(
            "The page loaded, but 'Winning numbers' was not found in its HTML text. "
            "The site may render results with JavaScript or may have changed its layout. "
            "Please enter the verified numbers manually."
        )

    section = text[marker.end():]
    stop = re.search(r"\b(divisions|prizes|prize\s+table|winners)\b", section, flags=re.I)
    if stop:
        section = section[:stop.start()]

    candidates = re.findall(r"(?<!\d)\d{1,2}(?!\d)", section)
    # Do not guess a range here; user sets the range in the sidebar.
    return candidates[:20], text[:500]


def frequency_table(draws, min_n, max_n):
    counts = {n: 0 for n in range(min_n, max_n + 1)}
    for draw in draws:
        for n in set(draw["numbers"]):
            if n in counts:
                counts[n] += 1
    df = pd.DataFrame({"Number": list(counts.keys()), "Appearances": list(counts.values())})
    return df.sort_values(["Appearances", "Number"], ascending=[False, True])


def candidate_combinations(draws, min_n, max_n, pick_count, how_many):
    freq = frequency_table(draws, min_n, max_n).set_index("Number")["Appearances"].to_dict()
    # Deterministic descriptive ranking only; not a forecast or improved odds.
    ranked = sorted(range(min_n, max_n + 1), key=lambda n: (-freq.get(n, 0), n))
    if len(ranked) < pick_count:
        return []
    base = ranked[:pick_count]
    combos = [base]
    for shift in range(1, min(how_many, 8)):
        rotated = ranked[shift:shift + pick_count]
        if len(rotated) == pick_count and rotated not in combos:
            combos.append(sorted(rotated))
    return combos[:how_many]


st.title("🎯 ZULTIBALL AI")
st.caption("ADVANCED DRAW ANALYSIS • STREAMLIT EDITION")
st.warning(
    "This is a statistical record-keeping and analysis tool, not a hack or winning system. "
    "Lottery draws are random; historical frequency cannot guarantee or reliably predict future results."
)

with st.sidebar:
    st.header("⚙️ Draw settings")
    min_n = st.number_input("Minimum number", min_value=0, max_value=999, value=DEFAULT_MIN, step=1)
    max_n = st.number_input("Maximum number", min_value=1, max_value=999, value=DEFAULT_MAX, step=1)
    if max_n < min_n:
        st.error("Maximum must be greater than or equal to minimum.")
    pick_count = st.number_input("Numbers in a draw", min_value=1, max_value=20, value=8, step=1)
    st.caption("Set these values to match the rules of the specific draw.")

tab_dash, tab_sync, tab_manual, tab_analysis, tab_history = st.tabs([
    "🏠 Dashboard", "🌐 Result page", "✍️ Add result", "📊 Analysis", "🗂️ History"
])

draws = load_draws()

with tab_dash:
    st.subheader("Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Saved draws", len(draws))
    c2.metric("Numbers per draw", int(pick_count))
    c3.metric("Configured range", f"{int(min_n)}–{int(max_n)}")
    st.markdown("### Latest saved result")
    if draws:
        latest = draws[0]
        st.write(f"Draw date: **{latest['draw_date'] or 'Not provided'}**")
        st.markdown("".join(
            f'<span class="number-pill">{n:02d}</span>' for n in latest["numbers"]
        ), unsafe_allow_html=True)
        if latest["source_url"]:
            st.caption(f"Source: {latest['source_url']}")
    else:
        st.info("No results saved yet. Add a verified result in the Result page or Add result tab.")

with tab_sync:
    st.subheader("Read a public Zulti draw page")
    st.write("Paste the URL of a specific public draw result page from Zulti.com.")
    draw_url = st.text_input("Official draw page URL", placeholder="https://zulti.com/draws/...")
    st.caption("This reads a public page only. It does not sign in, bypass restrictions, or discover new draw URLs.")
    if st.button("FETCH RESULT PAGE", key="fetch"):
        try:
            raw_numbers, excerpt = fetch_public_draw_page(draw_url.strip())
            st.text_area("Numbers detected in page section (review before saving)", ", ".join(raw_numbers), height=90)
            parsed = validate_numbers(raw_numbers, int(min_n), int(max_n))
            st.session_state["pending_numbers"] = parsed
            st.session_state["pending_url"] = draw_url.strip()
            if parsed:
                st.success(f"Detected {len(parsed)} distinct numbers within your configured range. Verify them against the official page.")
            else:
                st.warning("No valid numbers found within the configured range. You can enter the result manually.")
            st.caption("Page text preview:")
            st.code(excerpt)
        except Exception as exc:
            st.error(str(exc))
    pending = st.session_state.get("pending_numbers", [])
    if pending:
        st.write("Parsed numbers:", pending)
        pending_date = st.text_input("Draw date (optional)", key="pending_date")
        if st.button("SAVE VERIFIED RESULT", key="save_fetched"):
            if len(pending) != int(pick_count):
                st.error(f"Expected {int(pick_count)} numbers based on your settings, but detected {len(pending)}. Check settings or use manual entry.")
            else:
                save_draw(pending, pending_date, st.session_state.get("pending_url", ""))
                st.success("Verified result saved to local database.")
                st.session_state["pending_numbers"] = []
                st.rerun()

with tab_manual:
    st.subheader("Enter a verified result manually")
    date_value = st.text_input("Draw date (optional)", placeholder="YYYY-MM-DD")
    number_text = st.text_input("Winning numbers", placeholder="Example: 2, 4, 9, 26, 34, 36, 45, 48")
    if st.button("SAVE DRAW", key="manual_save"):
        raw = re.findall(r"\d+", number_text)
        nums = validate_numbers(raw, int(min_n), int(max_n))
        if len(nums) != int(pick_count):
            st.error(f"Please enter exactly {int(pick_count)} unique numbers within {int(min_n)}–{int(max_n)}.")
        else:
            save_draw(nums, date_value.strip(), "")
            st.success("Draw saved.")
            st.rerun()

with tab_analysis:
    st.subheader("Frequency analysis")
    if not draws:
        st.info("Save at least one verified draw to see analysis.")
    else:
        freq = frequency_table(draws, int(min_n), int(max_n))
        hot_count = min(10, len(freq))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Most frequent (hot)")
            st.dataframe(freq.head(hot_count), hide_index=True, use_container_width=True)
        with col2:
            st.markdown("#### Least frequent (cold)")
            st.dataframe(freq.sort_values(["Appearances", "Number"]).head(hot_count),
                         hide_index=True, use_container_width=True)
        st.markdown("#### Frequency chart")
        st.bar_chart(freq.set_index("Number")["Appearances"])
        st.markdown("#### Candidate combinations (frequency-ranked examples)")
        st.caption("These are descriptive combinations based on saved history, not predictions with a proven edge.")
        for i, combo in enumerate(candidate_combinations(draws, int(min_n), int(max_n),
                                                           int(pick_count), 5), start=1):
            st.write(f"**Set {i}:** " + " · ".join(f"{n:02d}" for n in combo))

with tab_history:
    st.subheader("Saved draw history")
    if draws:
        table = pd.DataFrame([{
            "ID": d["id"],
            "Draw date": d["draw_date"],
            "Winning numbers": ", ".join(f"{n:02d}" for n in d["numbers"]),
            "Source URL": d["source_url"],
            "Saved at": d["created_at"]
        } for d in draws])
        st.dataframe(table, hide_index=True, use_container_width=True)
        csv = table.to_csv(index=False).encode("utf-8")
        st.download_button("Download history CSV", csv, "zultiball_history.csv", "text/csv")
    else:
        st.info("No saved draw records.")

st.divider()
st.caption("Data note: Streamlit Community Cloud local files may be ephemeral across redeployments/restarts. For durable multi-user history, connect a hosted database.")
