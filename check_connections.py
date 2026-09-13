"""
check_connections.py -- standalone proof of communication with all 5
databases. Does nothing with the data itself; only verifies
each source is reachable, correctly identified, and genuinely live.
"""

import time
from db_config import connect

# database -> the one table we expect to find there, confirming we're
# actually talking to the right thing, not just any database
EXPECTED = {
    "roadcapture": "capture_log",
    "insurance": "policies",
    "rto_registration": "registrations",
    "theft_records": "theft_shredding",
    "vehicle_dwh": "vehicle_360",
}

print(f"{'DATABASE':<18}{'CONNECTED':<11}{'TABLE FOUND':<16}{'ROW COUNT':<11}{'LATENCY'}")
all_ok = True
for db, table in EXPECTED.items():
    start = time.perf_counter()
    try:
        conn = connect(db)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        (count,) = cur.fetchone()
        elapsed_ms = (time.perf_counter() - start) * 1000
        cur.close(); conn.close()
        print(f"{db:<18}{'YES':<11}{table:<16}{count:<11}{elapsed_ms:.1f} ms")
    except Exception as e:
        all_ok = False
        print(f"{db:<18}{'NO':<11}{'-':<16}{'-':<11}{type(e).__name__}: {e}")

print()
print("All 5 connections established successfully." if all_ok
      else "One or more connections FAILED -- see above.")
