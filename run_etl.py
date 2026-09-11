"""
run_etl.py -- extract, standardize, transform, decide, load, report.
Reads whatever is currently in the 4 MySQL source databases (built by
generate_data.py or hand-edited) -- does not touch or regenerate them.
Loads the result into vehicle_dwh.vehicle_360 on the same MySQL server.
"""

import re
from datetime import date
from db_config import connect

AS_OF = date(2026, 9, 12)


def fetchall(database, query):
    conn = connect(database)
    cur = conn.cursor()
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def normalize_plate(raw):
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


# ---------------- EXTRACT ----------------
captures = fetchall("roadcapture", "SELECT * FROM capture_log")
policies = fetchall("insurance", "SELECT * FROM policies")
regs = fetchall("rto_registration", "SELECT * FROM registrations")
thefts = fetchall("theft_records", "SELECT * FROM theft_shredding")

policy_by_plate = {normalize_plate(p["vehicle_number"]): p for p in policies}
reg_by_plate = {normalize_plate(r["reg_no"]): r for r in regs}
stolen_by_plate = {normalize_plate(t["plate_number"]): t for t in thefts}


# ---------------- TRANSFORM + DECIDE ----------------
def decide_status(plate):
    if plate in stolen_by_plate:
        return f"STOLEN/SHREDDED -> FLAG ({stolen_by_plate[plate]['report_type']})"
    pol = policy_by_plate.get(plate)
    if not pol:
        return "NO INSURANCE ON FILE -> FLAG"
    if pol["valid_to"] < AS_OF:
        return f"INSURANCE EXPIRED ({pol['valid_to']}) -> FLAG"
    return "OK - INSURED & CLEAR"


latest_capture_by_plate = {}
for c in captures:  # a vehicle can be captured more than once -- keep the latest sighting
    plate = normalize_plate(c["plate_no"])
    prev = latest_capture_by_plate.get(plate)
    if prev is None or c["capture_time"] > prev["capture_time"]:
        latest_capture_by_plate[plate] = c

rows = []
for plate, c in latest_capture_by_plate.items():  # anchor on vehicles actually seen on the road
    reg, pol = reg_by_plate.get(plate, {}), policy_by_plate.get(plate, {})
    theft = stolen_by_plate.get(plate, {})
    rows.append((
        plate, reg.get("owner_name"), reg.get("make_model"), reg.get("registration_date"),
        pol.get("insurer"), pol.get("valid_to"), theft.get("report_type", "-"),
        c["location"], c["capture_time"], decide_status(plate),
    ))

# ---------------- LOAD ----------------
wh = connect("vehicle_dwh")
wcur = wh.cursor()
wcur.execute("DROP TABLE IF EXISTS vehicle_360")
wcur.execute("""CREATE TABLE vehicle_360 (
    plate_canonical VARCHAR(20) PRIMARY KEY, owner_name VARCHAR(50), make_model VARCHAR(50),
    registration_date DATE, insurer VARCHAR(50), policy_valid_to DATE,
    theft_flag VARCHAR(20), last_seen_location VARCHAR(100), last_seen_time DATETIME,
    status VARCHAR(100))""")
wcur.executemany("INSERT INTO vehicle_360 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
wh.commit()

# ---------------- REPORT ----------------
total = len(rows)
by_bucket = {"OK": 0, "EXPIRED": 0, "STOLEN": 0, "NO INSURANCE": 0}
for r in rows:
    s = r[-1]
    if s.startswith("OK"): by_bucket["OK"] += 1
    elif "EXPIRED" in s: by_bucket["EXPIRED"] += 1
    elif "STOLEN" in s: by_bucket["STOLEN"] += 1
    else: by_bucket["NO INSURANCE"] += 1

print(f"vehicle_360 rows (distinct captured vehicles): {total}")
for k, v in by_bucket.items():
    print(f"  {k:14} {v:4}  ({v/total:.1%})")

print("\nSample flagged rows (first 8):")
print(f"{'PLATE':13}{'OWNER':19}{'MODEL':17}{'STATUS'}")
wcur.execute("SELECT plate_canonical, owner_name, make_model, status "
             "FROM vehicle_360 WHERE status NOT LIKE 'OK%' LIMIT 8")
for r in wcur.fetchall():
    print(f"{r[0]:13}{r[1]:19}{r[2]:17}{r[3]}")
wcur.close(); wh.close()

print(f"\nTotal flagged for Ministry report: {by_bucket['EXPIRED'] + by_bucket['STOLEN'] + by_bucket['NO INSURANCE']} of {total}")
