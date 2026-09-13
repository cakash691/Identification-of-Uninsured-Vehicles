"""
app.py -- simple GUI over the integrated warehouse (rubric item 8).

Two tabs, two users:
  "Look up a vehicle"  -- checkpoint officer, one plate, one verdict
  "Flagged vehicles"   -- Ministry analyst, the whole current picture

Run:  streamlit run app.py
"""

import re
import pandas as pd
import streamlit as st
from db_config import connect

st.set_page_config(page_title="Vehicle status lookup", layout="wide")

# severity order drives filter order, table sort, and colour choice
SEVERITY = {"Stolen / shredded": 0, "No insurance on file": 1,
            "Insurance expired": 2, "Clear": 3}

PALETTE = {
    "Stolen / shredded":    ("#FCEBEB", "#A32D2D", "#F09595"),
    "No insurance on file": ("#FAEEDA", "#854F0B", "#EF9F27"),
    "Insurance expired":    ("#F1EFE8", "#5F5E5A", "#B4B2A9"),
    "Clear":                ("#EAF3DE", "#3B6D11", "#97C459"),
}

ADVICE = {
    "Stolen / shredded":    "Detain and report to control room.",
    "No insurance on file": "No policy found in the insurance system.",
    "Insurance expired":    "Policy has lapsed. Issue notice.",
    "Clear":                "No action required.",
}


def normalize_plate(raw):
    """Same standardization the ETL uses -- user can type any source format."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def bucket(status):
    if status.startswith("OK"):
        return "Clear"
    if "EXPIRED" in status:
        return "Insurance expired"
    if "STOLEN" in status:
        return "Stolen / shredded"
    return "No insurance on file"


@st.cache_data(ttl=30)
def load_warehouse():
    conn = connect("vehicle_dwh")
    df = pd.read_sql("SELECT * FROM vehicle_360", conn)
    conn.close()
    return df


@st.cache_data(ttl=30)
def load_watermark():
    conn = connect("vehicle_dwh")
    cur = conn.cursor()
    cur.execute("SELECT last_processed_at FROM etl_watermark WHERE source_name='capture_log'")
    row = cur.fetchone()
    cur.close(); conn.close()
    return row[0] if row else None


try:
    df = load_warehouse()
except Exception as e:
    st.error(f"Could not reach the warehouse: {e}")
    st.stop()

if df.empty:
    st.warning("vehicle_360 is empty. Run generate_data.py and run_etl.py first.")
    st.stop()

df["category"] = df["status"].apply(bucket)
flagged = df[df["category"] != "Clear"]

# ------------------------------------------------------------------ header
head_l, head_r = st.columns([3, 1])
head_l.markdown("#### Vehicle status lookup")
watermark = load_watermark()
if watermark:
    head_r.markdown(
        f"<p style='text-align:right;font-size:13px;color:#5F5E5A;margin-top:12px'>"
        f"Refreshed to {watermark:%d %b %Y, %H:%M}</p>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
for col, label, value in [
    (m1, "Total vehicles", f"{len(df):,}"),
    (m2, "Flagged", f"{len(flagged):,}"),
    (m3, "Clear", f"{(df['category'] == 'Clear').sum():,}"),
    (m4, "Stolen / shredded", f"{(df['category'] == 'Stolen / shredded').sum():,}"),
]:
    col.markdown(
        f"<div style='background:#F7F6F3;border-radius:8px;padding:12px 14px'>"
        f"<div style='font-size:12px;color:#5F5E5A;margin-bottom:2px'>{label}</div>"
        f"<div style='font-size:22px;font-weight:500;color:#2C2C2A'>{value}</div></div>",
        unsafe_allow_html=True)

st.write("")
tab_lookup, tab_report = st.tabs(["Look up a vehicle", "Flagged vehicles"])

# ------------------------------------------------------------------ lookup
with tab_lookup:
    sc, _ = st.columns([1, 2])
    query = sc.text_input("Plate number",
                          placeholder="DL3CAB1234  /  DL-3-CAB-1234  /  dl 3 cab 1234")

    if query:
        plate = normalize_plate(query)
        hit = df[df["plate_canonical"] == plate]
        if hit.empty:
            st.warning(f"No record for {plate}. This vehicle has not been captured on the road.")
        else:
            r = hit.iloc[0]
            bg, fg, bd = PALETTE[r["category"]]
            label = "Insured and clear" if r["category"] == "Clear" else r["category"]
            st.markdown(
                f"<div style='background:{bg};border:1px solid {bd};border-radius:12px;"
                f"padding:16px 20px;margin:8px 0 16px'>"
                f"<div style='font-size:13px;font-family:monospace;color:{fg};opacity:.8'>"
                f"{r['plate_canonical']}</div>"
                f"<div style='font-size:20px;font-weight:500;color:{fg};margin:2px 0 4px'>{label}</div>"
                f"<div style='font-size:13px;color:{fg}'>{ADVICE[r['category']]}</div></div>",
                unsafe_allow_html=True)

            a, b = st.columns(2)
            with a.container(border=True):
                st.markdown("**Registration**")
                st.write(f"Owner — {r['owner_name'] or '—'}")
                st.write(f"Model — {r['make_model'] or '—'}")
                st.write(f"Registered — {r['registration_date'] or '—'}")
            with b.container(border=True):
                st.markdown("**Insurance**")
                st.write(f"Insurer — {r['insurer'] or 'None on file'}")
                st.write(f"Valid until — {r['policy_valid_to'] or '—'}")
                st.write(f"Theft record — {r['theft_flag']}")
            st.caption(f"Last seen at {r['last_seen_location']} on {r['last_seen_time']:%d %b %Y, %H:%M}")

            if r["category"] == "Stolen / shredded" and pd.notna(r["policy_valid_to"]):
                st.caption("Insurance is valid, but the theft record overrides it.")

# ------------------------------------------------------------------ report
with tab_report:
    categories = sorted(flagged["category"].unique(), key=lambda c: SEVERITY[c])
    chosen = st.multiselect("Filter by reason", categories, default=categories)

    view = (flagged[flagged["category"].isin(chosen)]
            .assign(_sev=lambda d: d["category"].map(SEVERITY))
            .sort_values(["_sev", "last_seen_time"], ascending=[True, False])
            .drop(columns="_sev"))

    st.caption(f"{len(view):,} of {len(df):,} captured vehicles flagged — "
               "most severe first, then most recently seen")

    table = (view[["plate_canonical", "owner_name", "make_model", "category",
                   "insurer", "policy_valid_to", "last_seen_location", "last_seen_time"]]
             .rename(columns={
                 "plate_canonical": "Plate", "owner_name": "Owner", "make_model": "Model",
                 "category": "Reason", "insurer": "Insurer", "policy_valid_to": "Valid until",
                 "last_seen_location": "Last seen", "last_seen_time": "Time"})
             .fillna("\u2014"))

    styled = table.style.apply(
        lambda col: [f"background-color:{PALETTE[v][0]};color:{PALETTE[v][1]}" for v in col],
        subset=["Reason"])

    st.dataframe(
        styled, use_container_width=True, hide_index=True, height=420,
        column_config={
            "Plate": st.column_config.TextColumn(width="small"),
            "Owner": st.column_config.TextColumn(width="small"),
            "Model": st.column_config.TextColumn(width="small"),
            "Reason": st.column_config.TextColumn(width="medium"),
            "Insurer": st.column_config.TextColumn(width="small"),
            "Valid until": st.column_config.TextColumn(width="small"),
            "Last seen": st.column_config.TextColumn(width="medium"),
            "Time": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm", width="small"),
        },
    )

    st.download_button(
        "Download report as CSV",
        view.to_csv(index=False).encode(),
        file_name="ministry_flagged_vehicles.csv",
        mime="text/csv",
    )
