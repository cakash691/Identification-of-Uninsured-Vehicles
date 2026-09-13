"""
run_etl.py -- extract, standardize, transform, decide, load, report.
Incremental: capture_log is extracted only for rows newer than the last
watermark, since it's the one table that grows continuously. The other
3 sources are small enough to re-pull in full each run -- no schema
change needed to support that. Load is an idempotent upsert keyed on
plate_canonical, so re-running never duplicates and is always safe.
"""

import re
from datetime import date, datetime
from db_config import connect

AS_OF = date(2026, 9, 12)
SENTINEL_START = datetime(2000, 1, 1)  # "beginning of time" for the very first run


def fetchall(database, query, params=None):
    conn = connect(database)
    cur = conn.cursor()
    cur.execute(query, params or ())
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def normalize_plate(raw):
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def get_watermark():
    wh = connect("vehicle_dwh")
    cur = wh.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS etl_watermark (
        source_name VARCHAR(50) PRIMARY KEY, last_processed_at DATETIME)""")
    cur.execute("SELECT last_processed_at FROM etl_watermark WHERE source_name='capture_log'")
    row = cur.fetchone()
    cur.close(); wh.close()
    return row[0] if row else SENTINEL_START


def set_watermark(new_watermark):
    wh = connect("vehicle_dwh")
    cur = wh.cursor()
    cur.execute("""INSERT INTO etl_watermark (source_name, last_processed_at) VALUES ('capture_log', %s)
                   ON DUPLICATE KEY UPDATE last_processed_at=VALUES(last_processed_at)""",
                (new_watermark,))
    wh.commit(); cur.close(); wh.close()


# ---------------- EXTRACT (incremental on capture_log only) ----------------
watermark = get_watermark()
new_captures = fetchall("roadcapture",
    "SELECT * FROM capture_log WHERE capture_time > %s", (watermark,))

print(f"Watermark going in: {watermark}")
print(f"New capture events since then: {len(new_captures)}")

if not new_captures:
    print("Nothing new -- exiting without touching the warehouse.")
else:
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

    latest_by_plate = {}
    for c in new_captures:  # a vehicle can appear more than once even within one delta
        plate = normalize_plate(c["plate_no"])
        prev = latest_by_plate.get(plate)
        if prev is None or c["capture_time"] > prev["capture_time"]:
            latest_by_plate[plate] = c

    rows = []
    for plate, c in latest_by_plate.items():
        reg, pol = reg_by_plate.get(plate, {}), policy_by_plate.get(plate, {})
        theft = stolen_by_plate.get(plate, {})
        rows.append((
            plate, reg.get("owner_name"), reg.get("make_model"), reg.get("registration_date"),
            pol.get("insurer"), pol.get("valid_to"), theft.get("report_type", "-"),
            c["location"], c["capture_time"], decide_status(plate),
        ))

    # ---------------- LOAD (upsert -- never drop, never reload what's unchanged) ----------------
    wh = connect("vehicle_dwh")
    wcur = wh.cursor()
    wcur.execute("""CREATE TABLE IF NOT EXISTS vehicle_360 (
        plate_canonical VARCHAR(20) PRIMARY KEY, owner_name VARCHAR(50), make_model VARCHAR(50),
        registration_date DATE, insurer VARCHAR(50), policy_valid_to DATE,
        theft_flag VARCHAR(20), last_seen_location VARCHAR(100), last_seen_time DATETIME,
        status VARCHAR(100))""")
    wcur.executemany("""INSERT INTO vehicle_360 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          owner_name=VALUES(owner_name), make_model=VALUES(make_model),
          registration_date=VALUES(registration_date), insurer=VALUES(insurer),
          policy_valid_to=VALUES(policy_valid_to), theft_flag=VALUES(theft_flag),
          last_seen_location=VALUES(last_seen_location), last_seen_time=VALUES(last_seen_time),
          status=VALUES(status)""", rows)
    wh.commit()

    new_watermark = max(c["capture_time"] for c in new_captures)
    set_watermark(new_watermark)

    print(f"-> {len(rows)} distinct vehicle(s) upserted into vehicle_360.")
    print(f"Watermark advanced to: {new_watermark}")

    # ---------------- REPORT (always the FULL current warehouse, not just this run's delta) ----------------
    wcur.execute("SELECT status FROM vehicle_360")
    by_bucket = {"OK": 0, "EXPIRED": 0, "STOLEN": 0, "NO INSURANCE": 0}
    for (s,) in wcur.fetchall():
        if s.startswith("OK"): by_bucket["OK"] += 1
        elif "EXPIRED" in s: by_bucket["EXPIRED"] += 1
        elif "STOLEN" in s: by_bucket["STOLEN"] += 1
        else: by_bucket["NO INSURANCE"] += 1
    total = sum(by_bucket.values())
    print(f"\nFull vehicle_360 status breakdown (cumulative across all runs so far, {total} vehicles):")
    for k, v in by_bucket.items():
        print(f"  {k:14} {v:5}  ({v/total:.1%})")
    wcur.close(); wh.close()
