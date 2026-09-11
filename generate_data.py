"""
generate_data.py -- populates the 4 independent source DATABASES at a realistic
scale, grounded in real (public) Indian vehicle/insurance conventions.
All individual records are fictional. Seeded for reproducibility.
"""

import random
from datetime import date, datetime, timedelta
from db_config import connect

random.seed(42)
AS_OF = date(2026, 9, 12)

N_VEHICLES = 5000
INSURANCE_COVERAGE = 0.92
EXPIRED_SHARE = 0.15
THEFT_SHARE = 0.045

# All 28 states + 8 union territories, real RTO state codes (verified against
# public RTO-code references, Sept 2026).
STATE_CODES = {
    "AN": "Andaman and Nicobar Islands", "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh",
    "AS": "Assam", "BR": "Bihar", "CH": "Chandigarh", "CG": "Chhattisgarh",
    "DD": "Dadra and Nagar Haveli and Daman and Diu", "DL": "Delhi", "GA": "Goa",
    "GJ": "Gujarat", "HR": "Haryana", "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir",
    "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala", "LA": "Ladakh",
    "LD": "Lakshadweep", "MP": "Madhya Pradesh", "MH": "Maharashtra", "MN": "Manipur",
    "ML": "Meghalaya", "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha",
    "PY": "Puducherry", "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim",
    "TN": "Tamil Nadu", "TS": "Telangana", "TR": "Tripura", "UP": "Uttar Pradesh",
    "UK": "Uttarakhand", "WB": "West Bengal",
}

# Weighted toward real Indian market-share leaders (Maruti/Hyundai/Tata dominant);
# 39 distinct models, repetition is the weighting mechanism (see chat).
MAKE_MODELS = (
    ["Maruti Swift"] * 8 + ["Maruti Baleno"] * 6 + ["Maruti WagonR"] * 6 +
    ["Maruti Dzire"] * 6 + ["Maruti Ertiga"] * 4 + ["Maruti Brezza"] * 4 +
    ["Maruti Alto"] * 5 + ["Maruti Celerio"] * 3 + ["Maruti Fronx"] * 3 +
    ["Maruti Grand Vitara"] * 2 +
    ["Hyundai Creta"] * 6 + ["Hyundai i20"] * 5 + ["Hyundai Venue"] * 4 +
    ["Hyundai Verna"] * 3 + ["Hyundai Exter"] * 2 +
    ["Tata Nexon"] * 5 + ["Tata Punch"] * 4 + ["Tata Altroz"] * 3 +
    ["Tata Tiago"] * 3 + ["Tata Harrier"] * 2 +
    ["Mahindra Scorpio"] * 4 + ["Mahindra XUV700"] * 3 + ["Mahindra Bolero"] * 3 +
    ["Mahindra Thar"] * 2 + ["Mahindra XUV300"] * 2 +
    ["Honda City"] * 4 + ["Honda Amaze"] * 2 + ["Honda Elevate"] * 2 +
    ["Toyota Innova"] * 3 + ["Toyota Fortuner"] * 2 + ["Toyota Glanza"] * 2 +
    ["Kia Seltos"] * 3 + ["Kia Sonet"] * 2 + ["Kia Carens"] * 2 +
    ["Renault Kwid"] * 2 + ["Nissan Magnite"] * 1 + ["Skoda Kushaq"] * 1 +
    ["Volkswagen Taigun"] * 1 + ["MG Hector"] * 1
)

# 25 real, IRDAI-registered (or historically so) Indian general insurers --
# verified via web search, Sept 2026.
INSURERS = ["ICICI Lombard", "HDFC Ergo", "Bajaj Allianz", "New India Assurance",
            "United India Insurance", "Oriental Insurance", "National Insurance",
            "Tata AIG", "Reliance General", "SBI General", "Go Digit", "Acko",
            "IFFCO Tokio", "Royal Sundaram", "Cholamandalam MS", "Liberty General",
            "Universal Sompo", "Zuno General", "Future Generali",
            "Zurich Kotak General Insurance", "Shriram General Insurance",
            "Magma HDI General Insurance", "Raheja QBE General Insurance",
            "Navi General Insurance", "Bharti AXA General Insurance"]

FIRST_NAMES = [
    "Ravi", "Amit", "Suresh", "Rajesh", "Manoj", "Arjun", "Sanjay", "Vikram", "Karan",
    "Rahul", "Vivek", "Ashok", "Deepak", "Anil", "Sunil", "Ramesh", "Naresh", "Mahesh",
    "Dinesh", "Yogesh", "Mukesh", "Rakesh", "Vishal", "Nitin", "Gaurav", "Rohit",
    "Aakash", "Siddharth", "Aditya", "Varun", "Anand", "Ajay", "Sameer", "Tarun",
    "Vinod", "Pankaj", "Alok", "Ankit", "Harish", "Rajiv", "Sandeep", "Girish", "Vijay",
    "Prakash", "Krishnan", "Balaji", "Suriya", "Naveen", "Praveen", "Sundaram",
    "Ganesh", "Murali", "Venkatesh", "Srinivas", "Rajan", "Mohan", "Karthik",
    "Debashish", "Subrata", "Amitava", "Partha", "Soumen", "Arindam", "Tapas",
    "Biswajit", "Jignesh", "Nikhil", "Hitesh", "Bhavesh", "Sachin", "Rohan",
    "Mangesh", "Prashant", "Sagar", "Nilesh", "Gurpreet", "Harpreet", "Manpreet",
    "Baljeet", "Bikash", "Hemanta", "Rijul", "Farhan", "Imran", "Zubin", "Tenzin",
    "Neha", "Priya", "Anita", "Pooja", "Kavita", "Sunita", "Deepa", "Meera", "Anjali",
    "Shreya", "Divya", "Kiran", "Rekha", "Sushma", "Usha", "Nisha", "Preeti", "Swati",
    "Ritu", "Seema", "Geeta", "Manju", "Vandana", "Renuka", "Shalini", "Nidhi",
    "Komal", "Payal", "Ekta", "Bhavna", "Lakshmi", "Kavya", "Meenakshi", "Deepika",
    "Swetha", "Sowmya", "Padma", "Radha", "Uma", "Anitha", "Revathi", "Jyothi",
    "Ananya", "Sreya", "Moushumi", "Bidisha", "Rina", "Mamata", "Sushmita", "Aditi",
    "Sneha", "Trupti", "Snehal", "Jasleen", "Simran", "Anima", "Farida", "Ayesha",
]

LAST_NAMES = [
    "Kumar", "Sharma", "Verma", "Singh", "Gupta", "Yadav", "Chauhan", "Tiwari",
    "Mishra", "Pandey", "Dubey", "Saxena", "Agarwal", "Bansal", "Jain", "Khanna",
    "Kapoor", "Malhotra", "Chopra", "Arora", "Bhatia", "Sethi", "Goel", "Aggarwal",
    "Rastogi", "Srivastava", "Tyagi", "Bhardwaj", "Chandra", "Nigam", "Awasthi",
    "Shukla", "Tripathi", "Reddy", "Nair", "Iyer", "Iyengar", "Menon", "Pillai",
    "Naidu", "Rao", "Rajan", "Krishnan", "Subramaniam", "Venkatesan", "Chettiar",
    "Gowda", "Shetty", "Hegde", "Kamath", "Pai", "Achar", "Bhat", "Chatterjee",
    "Bose", "Banerjee", "Mukherjee", "Ganguly", "Sen", "Dasgupta", "Chakraborty",
    "Bhattacharya", "Roy", "Das", "Ghosh", "Dutta", "Mitra", "Sarkar", "Patra",
    "Mohanty", "Nayak", "Sahoo", "Behera", "Panda", "Rout", "Patel", "Shah", "Mehta",
    "Desai", "Trivedi", "Vyas", "Joshi", "Doshi", "Thakkar", "Modi", "Parekh",
    "Deshmukh", "Kulkarni", "Patil", "Pawar", "Jadhav", "More", "Gaikwad", "Kadam",
    "Chavan", "Deshpande", "Bhosale", "Bajwa", "Sandhu", "Dhillon", "Grewal",
    "Sidhu", "Brar", "Chadha", "Ahluwalia", "Rathore", "Sisodia", "Bhati", "Solanki",
    "Baruah", "Bora", "Gogoi", "Saikia", "Hazarika", "Deka", "Phukan", "Dar", "Wani",
    "Khan", "Ansari", "Sheikh",
]

# Real, plausible location patterns rather than named landmarks for every one
# of the 36 states/UTs -- honest about which real places I could and couldn't
# confidently verify at that granularity (see chat).
LOCATION_KINDS = ["Toll Plaza", "Ring Road Camera", "Flyover Checkpoint",
                  "City Bypass Camera", "Highway Checkpoint", "Junction Camera"]


def gen_location(state_full_name):
    if random.random() < 0.5:
        return f"NH{random.randint(1, 166)} {random.choice(LOCATION_KINDS)}"
    return f"{state_full_name} {random.choice(LOCATION_KINDS)} {random.randint(1, 40)}"


COLORS = ["White", "Black", "Silver", "Red", "Blue", "Grey"]
VTYPES = ["Sedan", "SUV", "Hatchback"]


def gen_plate_components(state, used):
    while True:
        rto = random.randint(1, 50)
        series = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
        number = random.randint(1, 9999)
        key = (state, rto, series, number)
        if key not in used:
            used.add(key)
            return state, rto, series, number


def fmt_capture(s, r, sr, n):      return f"{s}{r}{sr}{n:04d}"
def fmt_insurance(s, r, sr, n):    return f"{s}-{r}-{sr}-{n:04d}"
def fmt_registration(s, r, sr, n): return f"{s}{r}{sr}{n:04d}".lower()
def fmt_theft(s, r, sr, n):        return f"{s} {r} {sr} {n:04d}"


used_keys = set()
vehicles = []
for i in range(N_VEHICLES):
    state = random.choice(list(STATE_CODES.keys()))
    comps = gen_plate_components(state, used_keys)
    vehicles.append({
        "comps": comps, "state": state,
        "owner": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "model": random.choice(MAKE_MODELS), "color": random.choice(COLORS),
        "vtype": random.choice(VTYPES),
        "reg_date": AS_OF - timedelta(days=random.randint(200, 3000)),
    })

# ---------------------------------------------------------------------------
# 1) roadcapture.capture_log
# ---------------------------------------------------------------------------
conn = connect("roadcapture")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS capture_log")
cur.execute("""CREATE TABLE capture_log (
    capture_id INT PRIMARY KEY AUTO_INCREMENT, plate_no VARCHAR(20),
    capture_time DATETIME, location VARCHAR(100),
    vehicle_color VARCHAR(20), vehicle_type VARCHAR(20))""")
cap_rows = []
as_of_dt = datetime(AS_OF.year, AS_OF.month, AS_OF.day)
for v in vehicles:
    plate = fmt_capture(*v["comps"])
    for _ in range(random.randint(1, 3)):
        loc = gen_location(STATE_CODES[v["state"]])
        ts = as_of_dt - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23),
                                   minutes=random.randint(0, 59))
        cap_rows.append((plate, ts, loc, v["color"], v["vtype"]))
cur.executemany("INSERT INTO capture_log (plate_no, capture_time, location, "
                 "vehicle_color, vehicle_type) VALUES (%s,%s,%s,%s,%s)", cap_rows)
conn.commit(); cur.close(); conn.close()

# ---------------------------------------------------------------------------
# 2) insurance.policies
# ---------------------------------------------------------------------------
conn = connect("insurance")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS policies")
cur.execute("""CREATE TABLE policies (
    policy_id INT PRIMARY KEY AUTO_INCREMENT, vehicle_number VARCHAR(20),
    insurer VARCHAR(50), valid_from DATE, valid_to DATE)""")
pol_rows = []
for v in vehicles:
    if random.random() > INSURANCE_COVERAGE:
        continue
    term = timedelta(days=365)
    if random.random() < EXPIRED_SHARE:
        vto = AS_OF - timedelta(days=random.randint(1, 200))
    else:
        vto = AS_OF + timedelta(days=random.randint(10, 360))
    vfrom = vto - term
    pol_rows.append((fmt_insurance(*v["comps"]), random.choice(INSURERS), vfrom, vto))
cur.executemany("INSERT INTO policies (vehicle_number, insurer, valid_from, valid_to) "
                 "VALUES (%s,%s,%s,%s)", pol_rows)
conn.commit(); cur.close(); conn.close()

# ---------------------------------------------------------------------------
# 3) rto_registration.registrations
# ---------------------------------------------------------------------------
conn = connect("rto_registration")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS registrations")
cur.execute("""CREATE TABLE registrations (
    reg_id INT PRIMARY KEY AUTO_INCREMENT, reg_no VARCHAR(20),
    owner_name VARCHAR(50), make_model VARCHAR(50), registration_date DATE)""")
reg_rows = [(fmt_registration(*v["comps"]), v["owner"], v["model"], v["reg_date"])
            for v in vehicles]
cur.executemany("INSERT INTO registrations (reg_no, owner_name, make_model, "
                 "registration_date) VALUES (%s,%s,%s,%s)", reg_rows)
conn.commit(); cur.close(); conn.close()

# ---------------------------------------------------------------------------
# 4) theft_records.theft_shredding
# ---------------------------------------------------------------------------
conn = connect("theft_records")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS theft_shredding")
cur.execute("""CREATE TABLE theft_shredding (
    case_id INT PRIMARY KEY AUTO_INCREMENT, plate_number VARCHAR(20),
    report_type VARCHAR(20), report_date DATE)""")
theft_rows = []
flagged = random.sample(vehicles, k=max(1, round(N_VEHICLES * THEFT_SHARE)))
for v in flagged:
    rdate = AS_OF - timedelta(days=random.randint(5, 400))
    theft_rows.append((fmt_theft(*v["comps"]), random.choice(["STOLEN", "SHREDDED"]), rdate))
for _ in range(3):
    state = random.choice(list(STATE_CODES.keys()))
    comps = gen_plate_components(state, used_keys)
    rdate = AS_OF - timedelta(days=random.randint(30, 500))
    theft_rows.append((fmt_theft(*comps), random.choice(["STOLEN", "SHREDDED"]), rdate))
cur.executemany("INSERT INTO theft_shredding (plate_number, report_type, report_date) "
                 "VALUES (%s,%s,%s)", theft_rows)
conn.commit(); cur.close(); conn.close()

print(f"vehicles (universe):        {N_VEHICLES}")
print(f"capture_log rows:           {len(cap_rows)}  (across {len(set(r[0] for r in cap_rows))} distinct plates)")
print(f"policies rows:              {len(pol_rows)}  ({len(pol_rows)/N_VEHICLES:.0%} coverage)")
print(f"registrations rows:         {len(reg_rows)}  (100% coverage)")
print(f"theft_shredding rows:       {len(theft_rows)}  ({len(flagged)} tied to captured vehicles, 3 phantom)")
print("Databases: roadcapture, insurance, rto_registration, theft_records (MySQL, localhost)")
