"""
export_sample.py -- writes a small, illustrative slice of each table to
sample_data/. NOT the real dataset: it exists so someone browsing the repo
can see the four plate formats without installing MySQL.

The vehicles are hand-picked to cover all four outcomes and are THE SAME
across all files, so one vehicle can be traced end to end.
"""

import os, re, warnings
import pandas as pd
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
from db_config import connect

os.makedirs("sample_data", exist_ok=True)

def norm(p): return re.sub(r"[^A-Z0-9]", "", p.upper())

wh = connect("vehicle_dwh")
v360 = pd.read_sql("SELECT * FROM vehicle_360", wh); wh.close()

def bucket(s):
    if s.startswith("OK"): return "Clear"
    if "EXPIRED" in s: return "Insurance expired"
    if "STOLEN" in s: return "Stolen / shredded"
    return "No insurance on file"
v360["category"] = v360["status"].apply(bucket)

# 2 per outcome, spread across different states so the sample does not
# look like the dataset only covers one region. Deterministic: no RNG,
# just first-seen per distinct state code.
v360["state"] = v360.plate_canonical.str[:2]

def pick(frame, n, used_states):
    out = []
    for _, row in frame.sort_values("plate_canonical").iterrows():
        if row.state in used_states:
            continue
        used_states.add(row.state)
        out.append(row.plate_canonical)
        if len(out) == n:
            break
    return out

used = set()
picks = []
stolen_insured = v360[(v360.category == "Stolen / shredded") & v360.policy_valid_to.notna()]
picks += pick(stolen_insured, 2, used)
for cat in ["Insurance expired", "No insurance on file", "Clear"]:
    picks += pick(v360[v360.category == cat], 2, used)
picks = sorted(set(picks))
print("sample vehicles:", picks)

def dump(db, table, plate_col, rows, name):
    conn = connect(db)
    df = pd.read_sql(f"SELECT * FROM {table}", conn); conn.close()
    sel = df[df[plate_col].apply(norm).isin(rows)].sort_values(plate_col)
    sel.to_csv(f"sample_data/{name}.csv", index=False)
    print(f"  {name}.csv -> {len(sel)} rows")
    return sel

s_cap = dump("roadcapture", "capture_log", "plate_no", picks, "capture_log")
s_pol = dump("insurance", "policies", "vehicle_number", picks, "policies")
s_reg = dump("rto_registration", "registrations", "reg_no", picks, "registrations")
s_thf = dump("theft_records", "theft_shredding", "plate_number", picks, "theft_shredding")

s_360 = v360[v360.plate_canonical.isin(picks)].drop(columns=["category", "state"]).sort_values("plate_canonical")
s_360.to_csv("sample_data/vehicle_360.csv", index=False)
print(f"  vehicle_360.csv -> {len(s_360)} rows")
