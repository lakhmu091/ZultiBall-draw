import re
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="ZULTIBALL AI", page_icon="🎯", layout="wide")
st.markdown("""
<style>
.stApp{background:#080d0b;color:#e8f5ec}
[data-testid="stSidebar"]{background:#0c1710}
h1,h2,h3{color:#54ff85!important}
div.stButton>button{background:#10251a;color:#54ff85;border:1px solid #287c42;border-radius:10px;font-weight:700}
div[data-testid="stMetric"]{background:#10251a;border:1px solid #245536;padding:12px;border-radius:12px}
.pill{display:inline-block;background:#10251a;color:#54ff85;border:1px solid #287c42;padding:9px 13px;margin:4px;border-radius:10px;font-weight:700}
</style>
""", unsafe_allow_html=True)

DB = "zultiball.db"

def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS draws(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draw_date TEXT, source_url TEXT, numbers TEXT, created_at TEXT)""")
    c.commit()
    return c

def save(nums, date="", url=""):
    c=db()
    c.execute("INSERT INTO draws(draw_date,source_url,numbers,created_at) VALUES(?,?,?,?)",
              (date,url,",".join(map(str,nums)),datetime.now(timezone.utc).isoformat()))
    c.commit(); c.close()

def history():
    c=db()
    rows=c.execute("SELECT id,draw_date,source_url,numbers,created_at FROM draws ORDER BY id DESC").fetchall()
    c.close()
    return [{"id":r[0],"date":r[1],"url":r[2],"numbers":[int(x) for x in r[3].split(",") if x],"saved":r[4]} for r in rows]

def clean_nums(raw, lo, hi):
    out=[]
    for x in raw:
        try: n=int(x)
        except: continue
        if lo <= n <= hi and n not in out: out.append(n)
    return sorted(out)

def fetch_page(url):
    p=urlparse(url)
    if p.scheme!="https" or p.netloc.lower() not in ("zulti.com","www.zulti.com"):
        raise ValueError("Only public HTTPS URLs on zulti.com are allowed.")
    if not p.path.startswith("/draws/"):
        raise ValueError("Use a public result link beginning https://zulti.com/draws/")
    r=requests.get(url,timeout=25,headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    # Try visible page text first, then embedded script/JSON text.
    visible=soup.get_text(" ",strip=True)
    combined=visible+" "+r.text
    patterns=[
        r"winning\s+numbers.{0,500}?(?:(?:<[^>]+>)|[\s,;:])*((?:\d{1,2}[\s,;:<\/>\"']+){5,9}\d{1,2})",
        r"winningNumbers.{0,300}?((?:\d{1,2}\D+){5,9}\d{1,2})",
        r'"winningNumbers"\s*:\s*\[([^\]]+)\]',
        r'"winning_numbers"\s*:\s*\[([^\]]+)\]'
    ]
    for pat in patterns:
        m=re.search(pat,combined,re.I|re.S)
        if m:
            vals=re.findall(r"\d{1,2}",m.group(1))
            if 5 <= len(vals) <= 10:
                return vals, visible[:700], "Found a candidate result section in page content."
    # No reliable number cluster found: do not guess from unrelated page numbers.
    return [], visible[:1000], "The website response did not expose a reliably identifiable winning-number list. It may be client-rendered or structured differently."

st.title("🎯 ZULTIBALL AI")
st.caption("ADVANCED DRAW ANALYSIS • STREAMLIT EDITION")
st.warning("Statistics describe past results only. Lottery draws are random; no analysis can guarantee or reliably predict winning numbers.")

with st.sidebar:
    st.header("Draw rules")
    lo=st.number_input("Minimum number",0,999,1)
    hi=st.number_input("Maximum number",1,999,49)
    picks=st.number_input("Numbers in this draw",1,20,7)
    st.caption("Current Zultiball examples can have 7 or 8 numbers. Set the count for the specific draw you are entering.")

draws=history()
tabs=st.tabs(["Dashboard","Fetch result page","Manual verified entry","Analysis","History"])

with tabs[0]:
    a,b,c=st.columns(3)
    a.metric("Saved draws",len(draws)); b.metric("Numbers per draw",picks); c.metric("Configured range",f"{lo}–{hi}")
    st.subheader("Latest saved result")
    if draws:
        d=draws[0]
        st.write("Draw date:",d["date"] or "Not supplied")
        st.markdown("".join(f'<span class="pill">{n:02d}</span>' for n in d["numbers"]),unsafe_allow_html=True)
        if d["url"]: st.caption(d["url"])
    else: st.info("No saved results yet.")

with tabs[1]:
    st.subheader("Read public Zulti result page")
    st.info("The page reader is best-effort. Zulti may render result content in the browser rather than the HTML returned to Streamlit. If it cannot identify the numbers, use the verified manual-entry tab.")
    url=st.text_input("Public draw result URL",placeholder="https://zulti.com/draws/...")
    if st.button("TRY FETCHING RESULT"):
        try:
            raw,preview,msg=fetch_page(url.strip())
            st.write(msg)
            st.text_area("Page text preview",preview,height=140)
            parsed=clean_nums(raw,int(lo),int(hi))
            if parsed:
                st.session_state["candidate"]=parsed
                st.session_state["candidate_url"]=url.strip()
                st.success("Candidate numbers found. Compare them with the official Zulti result page before saving.")
                st.write("Candidate:",parsed)
            else:
                st.warning("No verified candidate number list was detected. No data was saved.")
                st.caption("This is a page-rendering/parser limitation, not proof that the draw result is missing.")
        except Exception as e:
            st.error(f"Fetch failed: {e}")
    cand=st.session_state.get("candidate",[])
    if cand:
        st.write("Review candidate numbers:",cand)
        ddate=st.text_input("Draw date",key="candidate_date")
        if st.button("SAVE AFTER VERIFYING"):
            if len(cand)!=int(picks):
                st.error(f"Configured count is {picks}, but candidate has {len(cand)} numbers. Adjust the sidebar or enter manually.")
            else:
                save(cand,ddate,st.session_state.get("candidate_url",""))
                st.session_state.pop("candidate",None); st.success("Saved."); st.rerun()

with tabs[2]:
    st.subheader("Manual verified entry")
    st.write("Open the official result page in another browser tab, copy the winning numbers, and enter them here.")
    st.link_button("Open Zulti.com","https://zulti.com/")
    md=st.text_input("Draw date (optional)",placeholder="YYYY-MM-DD")
    mu=st.text_input("Official result URL (optional)",placeholder="https://zulti.com/draws/...")
    nums=st.text_input("Winning numbers",placeholder="11, 21, 23, 30, 37, 43, 49")
    if st.button("SAVE VERIFIED DRAW"):
        if mu and (urlparse(mu).netloc.lower() not in ("zulti.com","www.zulti.com") or not mu.startswith("https://")):
            st.error("Source URL must be an HTTPS Zulti.com link.")
        else:
            parsed=clean_nums(re.findall(r"\d+",nums),int(lo),int(hi))
            if len(parsed)!=int(picks):
                st.error(f"Expected exactly {picks} unique numbers between {lo} and {hi}; found {len(parsed)}.")
            else:
                save(parsed,md,mu); st.success("Verified draw saved."); st.rerun()

with tabs[3]:
    st.subheader("Historical frequency analysis")
    if not draws: st.info("Add verified draw results first.")
    else:
        counts={n:0 for n in range(int(lo),int(hi)+1)}
        for d in draws:
            for n in set(d["numbers"]):
                if n in counts: counts[n]+=1
        df=pd.DataFrame({"Number":list(counts),"Appearances":list(counts.values())})
        hot=df.sort_values(["Appearances","Number"],ascending=[False,True])
        cold=df.sort_values(["Appearances","Number"],ascending=[True,True])
        x,y=st.columns(2)
        with x: st.markdown("#### Hot numbers"); st.dataframe(hot.head(10),hide_index=True,use_container_width=True)
        with y: st.markdown("#### Cold numbers"); st.dataframe(cold.head(10),hide_index=True,use_container_width=True)
        st.bar_chart(df.set_index("Number"))
        st.caption("Frequency-ranked examples are descriptive, not predictions with a proven advantage.")
        ranked=hot["Number"].tolist()
        st.markdown("#### Frequency-ranked sample combination")
        st.write(" · ".join(f"{n:02d}" for n in sorted(ranked[:int(picks)])))

with tabs[4]:
    st.subheader("Draw history")
    if draws:
        table=pd.DataFrame([{"ID":d["id"],"Date":d["date"],"Numbers":", ".join(f"{n:02d}" for n in d["numbers"]),"Source":d["url"],"Saved":d["saved"]} for d in draws])
        st.dataframe(table,hide_index=True,use_container_width=True)
        st.download_button("Download CSV",table.to_csv(index=False).encode(), "zultiball_history.csv","text/csv")
    else: st.info("No saved records.")

st.divider()
st.caption("No private endpoints, account access, or server manipulation. Streamlit Community Cloud local storage may not persist across restarts; use a hosted database for durable history.")
