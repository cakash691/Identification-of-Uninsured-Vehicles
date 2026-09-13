# Identification of Uninsured Vehicles

**CSE656 — Information Integration and Applications · Part A**
Akash Chakraborty (MT25013), IIIT-Delhi
Instructor: Prof. Mukesh Mohania

---

## Overview

Vehicle records in India live in systems that were never designed to talk to each
other. The camera that reads a number plate on a highway, the insurer that issued
the policy, the RTO that registered the vehicle, and the police record that marked
it stolen are four separate databases, built by four separate bodies, using four
separate conventions for the same piece of information.

This project integrates those four sources into a single warehouse table
(`vehicle_360`) that answers one operational question: **given a vehicle observed
on the road right now, is it legally allowed to be there?**

The integration is non-trivial because the join key itself is inconsistent. The
same vehicle appears as:

| Source system | Column name | Format on record |
|---|---|---|
| On-road capture | `plate_no` | `DL3CAB1234` |
| Insurance | `vehicle_number` | `DL-3-CAB-1234` |
| RTO registration | `reg_no` | `dl3cab1234` |
| Theft / shredding | `plate_number` | `DL 3 CAB 1234` |

Four column names, four formats, one real-world vehicle. Resolving that is the
core of the work.

---

## 1. Scope of work

This project addresses identifying uninsured, unregistered, or stolen vehicles at
the point they are observed on the road, by integrating four structured data
sources that are designed and maintained independently of each other: an on-road
vehicle-capture system, an insurance-policy system, the official vehicle
registration (RTO) system, and a theft-and-shredding record system.

For Part A, the scope covers designing a representative schema for each of the
four sources and populating them with realistic sample data; building a
deterministic extraction and key-standardization layer that resolves the same
vehicle appearing under different column names and plate-number formats across
sources; transforming and loading the integrated result into a single warehouse
table (`vehicle_360`) via explicit business rules; and exposing that result
through a simple GUI supporting plate lookup and a Ministry-of-Transportation-style
flagged-vehicle report.

Since the brief does not specify a required mechanism for "establishing
communication between the data sources," this project treats the ETL layer's
ability to independently connect to and extract from each of the four separately
hosted databases as satisfying that requirement, rather than a live network-service
architecture between the sources themselves.

Handling ambiguous or uncertain matches — OCR misreads, near-duplicate identity
records — is explicitly out of scope here and deferred to Part B, as is
unstructured-content integration and natural-language querying, which is Part C's
focus.

---

## 2. New / innovative aspects

**Decision-centric fusion rather than record merging.** When a vehicle's records
conflict across sources — a stolen vehicle whose insurance happens to still be
active, for instance — an explicit, severity-ordered business rule resolves this
into one actionable status. Theft or shredding overrides insurance status, which
overrides a clean record. This directly answers the brief's stated goal of moving
from heterogeneous data to decision-centric integration, rather than simply
producing a wider table. In the current dataset, 208 vehicles are flagged stolen
while still holding a policy that would otherwise read as valid; a naive join
would report these as insured.

**Capture-anchored integration.** The pipeline is anchored on the on-road capture
log as the driving table rather than performing a blind outer join across all four
sources. The system therefore only ever reports on vehicles actually observed on
the road, not every historical record regardless of present relevance. Theft
records for vehicles never captured are correctly excluded from the report.

**Idempotent incremental loading.** The warehouse load is a watermark-driven
incremental upsert keyed on the standardized plate, not a full rebuild per run.
Re-running the ETL with no new captures performs no work; a vehicle seen fifty
times occupies one row, refreshed in place. The standardization step is isolated
on its own, so Part B's uncertainty-aware matching and Part C's NLQ layer extend
this same pipeline rather than requiring Part A to be rebuilt.

---

## 3. Architecture

```
  roadcapture.capture_log ─┐
  insurance.policies ──────┤
  rto_registration.        ├──▶  run_etl.py  ──▶  vehicle_dwh.vehicle_360  ──▶  app.py
    registrations ─────────┤     extract            one row per vehicle         Streamlit GUI
  theft_records.           │     standardize        + etl_watermark
    theft_shredding ───────┘     decide
                                 upsert
```

Five MySQL databases on one server. The four sources hold no foreign keys to each
other — they are independent by design. Correspondence between them exists only
inside the ETL layer.

**Decision logic**, applied per captured vehicle, in strict order:

1. Present in theft/shredding records → flag (stolen or shredded)
2. No insurance policy on file → flag
3. Policy `valid_to` earlier than today → flag (expired)
4. Otherwise → clear

---

## 4. Repository contents

| File | Purpose |
|---|---|
| `setup_mysql.sql` | One-time: creates the 5 databases and the `iia_app` user |
| `db_config.py` | Shared MySQL connection settings |
| `generate_data.py` | Populates the 4 source databases with realistic sample data |
| `run_etl.py` | Extract → standardize → decide → incremental upsert into `vehicle_360` |
| `check_connections.py` | Standalone proof that all 5 databases are reachable |
| `app.py` | Streamlit GUI: plate lookup + flagged-vehicle report |
| `.streamlit/config.toml` | GUI theme |

---

## 5. Setup from scratch (macOS)

### Prerequisites

Homebrew. If `brew --version` fails, install it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Run the PATH lines it prints at the end, then open a new terminal tab.

### Step 1 — Install MySQL and Python

```bash
brew install mysql python
brew services start mysql
```

Wait ~10 seconds for the server to come up. Confirm with `brew services list` —
the `mysql` row should read `started`.

### Step 2 — Get the project

```bash
git clone https://github.com/cakash691/Identification-of-Uninsured-Vehicles.git
cd Identification-of-Uninsured-Vehicles
```

### Step 3 — Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install mysql-connector-python pandas streamlit
```

Your prompt should now begin with `(venv)`. **This must be re-run in every new
terminal session** — `source venv/bin/activate` — or Python will not find the
MySQL driver.

Verify:

```bash
python3 -c "import mysql.connector; print(mysql.connector.__version__)"
```

### Step 4 — Create the databases and application user

```bash
mysql -u root -p < setup_mysql.sql
```

Enter your MySQL root password. **Success prints nothing** — the statements in
that file produce no output. That is expected.

This creates five databases (`roadcapture`, `insurance`, `rto_registration`,
`theft_records`, `vehicle_dwh`) and an `iia_app` user scoped to `127.0.0.1`.

Verify:

```bash
mysql -u root -p -e "SHOW DATABASES;"
mysql -u root -p -e "SELECT user, host FROM mysql.user WHERE user='iia_app';"
```

The second should return exactly one row: `iia_app | 127.0.0.1`.

### Step 5 — Confirm connectivity

```bash
python3 check_connections.py
```

Every row should read `YES`. If any read `NO`, stop here — later steps will fail.

---

## 6. Running the application

### Generate the source data

```bash
python3 generate_data.py
```

Expected output:

```
vehicles (universe):        5000
capture_log rows:           9912  (across 5000 distinct plates)
policies rows:              4590  (92% coverage)
registrations rows:         5000  (100% coverage)
theft_shredding rows:       228   (225 tied to captured vehicles, 3 phantom)
```

The generator is seeded (`random.seed(42)`), so this produces byte-identical data
on every machine and every run. To change the scale, edit `N_VEHICLES` at the top
of the file.

### Run the ETL

```bash
python3 run_etl.py
```

First run processes everything:

```
Watermark going in: 2000-01-01 00:00:00
New capture events since then: 9912
-> 5000 distinct vehicle(s) upserted into vehicle_360.

Full vehicle_360 status breakdown (cumulative across all runs so far, 5000 vehicles):
  OK              3683  (73.7%)
  EXPIRED          699  (14.0%)
  STOLEN           225  (4.5%)
  NO INSURANCE     393  (7.9%)
```

Run it a second time immediately and it will report `New capture events since
then: 0` and exit without touching the warehouse. That is the incremental
behaviour working correctly, not a failure.

### Launch the GUI

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Two tabs:

- **Look up a vehicle** — enter a plate in any format (`DL3CAB1234`,
  `DL-3-CAB-1234`, `dl 3 cab 1234` all resolve to the same record) and get owner,
  model, insurance status, and a verdict.
- **Flagged vehicles** — the full Ministry report, filterable by reason, sorted
  most-severe-first then most-recent, downloadable as CSV.

---

## 7. Demonstrating the incremental refresh

To show incremental loading live rather than describing it:

```bash
# 1. Note the current state
python3 run_etl.py          # reports 0 new events

# 2. Simulate a new road sighting
mysql -u iia_app -piia_app_pw -h 127.0.0.1 roadcapture -e \
  "INSERT INTO capture_log (plate_no, capture_time, location, vehicle_color, vehicle_type)
   VALUES ('ZZ99XX9999', '2026-09-12 09:30:00', 'Test Camera 1', 'Black', 'SUV');"

# 3. Re-run
python3 run_etl.py          # reports exactly 1 new event, not 9913
```

`ZZ99XX9999` exists in no source system, so it is correctly inserted with a null
owner and flagged `NO INSURANCE ON FILE`. Re-sighting a plate already in the
warehouse updates its row in place instead of duplicating it.

Useful demo plate: **`AN28QJ3214`** — flagged stolen while holding a
valid-looking policy. The lookup tab shows the override reasoning explicitly.

---

## 8. Schema reference

**`roadcapture.capture_log`** — on-road sightings, the driving table
`capture_id` (PK), `plate_no`, `capture_time`, `location`, `vehicle_color`, `vehicle_type`

**`insurance.policies`** — policy records
`policy_id` (PK), `vehicle_number`, `insurer`, `valid_from`, `valid_to`

**`rto_registration.registrations`** — official registration
`reg_id` (PK), `reg_no`, `owner_name`, `make_model`, `registration_date`

**`theft_records.theft_shredding`** — theft and scrappage cases
`case_id` (PK), `plate_number`, `report_type`, `report_date`

**`vehicle_dwh.vehicle_360`** — integrated warehouse, one row per captured vehicle
`plate_canonical` (PK), `owner_name`, `make_model`, `registration_date`,
`insurer`, `policy_valid_to`, `theft_flag`, `last_seen_location`,
`last_seen_time`, `status`

**`vehicle_dwh.etl_watermark`** — incremental-load bookkeeping
`source_name` (PK), `last_processed_at`

---

## 9. How the sample data is generated

All records are fictional, but built from real, publicly documented conventions so
the dataset behaves like real data rather than noise:

- **Plate format** follows the actual Indian pattern (state code + RTO code +
  series + number), across all 28 states and 8 union territories with their real
  RTO codes.
- **Insurers** are 25 genuine IRDAI-registered general insurers.
- **Vehicle models** are 39 real models, weighted toward actual Indian market
  share (Maruti and Hyundai dominant) by repeating entries in the source list.
- **Owner names** are drawn from 144 first names and 121 surnames spanning
  multiple Indian regional naming traditions.
- **Coverage is deliberately imperfect**: ~92% of vehicles carry a policy, ~15% of
  those have lapsed, ~4.5% appear in theft records, and 3 theft cases reference
  vehicles never captured on the road.

Locations are generated as realistic patterns (`NH84 Toll Plaza`, `Kerala Ring
Road Camera 17`) rather than named landmarks, since specific real toll plazas
could not be verified for all 36 states and territories.

---

## 10. Design decisions and known limitations

**Schema correspondence is hand-specified, not algorithmically discovered.**
The mapping between `plate_no`, `vehicle_number`, `reg_no`, and `plate_number` is
asserted in `run_etl.py` rather than derived by a matching algorithm. This is a
deliberate Global-as-View choice: with four stable sources fully known to the
integrator, hand-specified mapping is the appropriate technique, and every
automated matching pipeline terminates in human validation regardless. Worth
noting that purely lexical matching would *fail* on this dataset — `plate_no` and
`vehicle_number` share no tokens and score 0.00 on raw name similarity. Automated
discovery here would require instance-based evidence (the shared plate value
pattern), which is Part B territory.

**Credentials are stored in plaintext** in `db_config.py`. Acceptable for a local
academic project with a throwaway password; a production system would use
environment variables or a secrets manager.

**The ETL is periodic batch, not event-driven.** There is no trigger firing per
captured vehicle. Whatever has accumulated in `capture_log` since the last run is
processed together on the next invocation. This is standard warehouse practice,
but it means `vehicle_360` is as fresh as the last ETL run, not as fresh as the
last camera sighting.

**Only `capture_log` is extracted incrementally.** The other three sources are
small and re-pulled in full each run. Scaling them incrementally would need
change-tracking columns they do not currently carry.

---