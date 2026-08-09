"""
generate_data.py
-----------------
Generates a realistic SYNTHETIC dataset of digital-payment (UPI) customer
support complaints, modeled on:
  - The complaint category taxonomy published by the RBI Ombudsman Scheme
    for Digital Transactions, 2019.
  - Approximate Turn-Around-Time (TAT) windows loosely based on RBI's
    "Harmonisation of TAT and customer compensation for failed transactions
    using authorised Payment Systems" circular (RBI/2019-20/67).
  - Realistic support-operations patterns observed in live digital-payments
    customer support work (volume spikes around salary dates, incident days
    causing technical-error surges, fraud/dispute cases taking longest to
    resolve).

No real customer, transaction, or company data is used anywhere in this
project. All records are synthetically generated for portfolio purposes.

Output: 4 CSV files written to ../data/
  - dim_category.csv
  - dim_channel.csv
  - dim_agent.csv
  - fact_complaints.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# 0. Setup
# ----------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

START_DATE = datetime(2025, 8, 1)
END_DATE = datetime(2026, 7, 30)  # "today"
TOTAL_DAYS = (END_DATE - START_DATE).days + 1

# ----------------------------------------------------------------------
# 1. Dimension: Complaint categories
#    sla_target_hours are illustrative TAT windows, not an exact
#    reproduction of any bank's or regulator's real published table.
# ----------------------------------------------------------------------
categories = pd.DataFrame([
    # category_id, category_name, category_group, sla_target_hours, base_weight
    (1, "Transaction Failed - Amount Debited (Auto-Reversal Pending)", "Failed Transaction", 24,  0.20),
    (2, "Refund Delayed / Not Received",                                "Refunds",            120, 0.16),
    (3, "Unauthorized Transaction / Fraud Dispute",                     "Fraud & Disputes",    168, 0.08),
    (4, "Amount Debited but Not Credited to Beneficiary",                "Failed Transaction", 48,  0.13),
    (5, "Duplicate Debit for Same Transaction",                          "Failed Transaction", 72,  0.07),
    (6, "KYC / Account Verification Issue",                              "Account & KYC",       96,  0.06),
    (7, "Merchant / QR Payment Failure",                                 "Merchant Payments",   48,  0.11),
    (8, "App Technical Error (Login / OTP Blocking Payment)",            "Technical",           24,  0.10),
    (9, "Wrong Beneficiary Credited (Misdirected Transfer)",             "Fraud & Disputes",    120, 0.04),
    (10, "Cashback / Reward Not Credited",                               "Rewards",             168, 0.05),
], columns=["category_id", "category_name", "category_group", "sla_target_hours", "base_weight"])

# Root causes each category can be tagged with once resolved
ROOT_CAUSES = {
    1: ["Bank-side auto-reversal delay", "Payment gateway timeout", "NPCI switch downtime", "Manual reversal required"],
    2: ["Refund batch job delay", "Bank processing delay", "Incorrect refund account on file", "Merchant refund not initiated"],
    3: ["Confirmed phishing/OTP-sharing fraud", "SIM-swap fraud", "Card-not-present fraud", "False positive - user forgot transaction"],
    4: ["Beneficiary bank server issue", "IFSC/account mismatch", "NPCI settlement delay", "Beneficiary account frozen"],
    5: ["Network retry causing duplicate debit", "User double-tap on payment button", "Merchant terminal glitch"],
    6: ["Document mismatch", "PAN-Aadhaar link pending", "Video KYC slot unavailable", "Manual review backlog"],
    7: ["Merchant QR misconfigured", "Merchant bank account inactive", "POS/QR gateway timeout"],
    8: ["App version bug post-release", "OTP delivery delay from telecom", "Server outage", "Login token expiry bug"],
    9: ["User entered wrong UPI ID", "Similar beneficiary name confusion", "Contact sync error in app"],
    10: ["Rewards batch processing delay", "Promotion terms not met", "Cashback engine bug"],
}

# ----------------------------------------------------------------------
# 2. Dimension: Channels
# ----------------------------------------------------------------------
channels = pd.DataFrame([
    (1, "UPI App-to-App Transfer"),
    (2, "Merchant QR Payment"),
    (3, "Bill / Recharge Payment"),
    (4, "Bank-Linked Bank Transfer"),
    (5, "Peer-to-Peer (Contact) Transfer"),
], columns=["channel_id", "channel_name"])

# ----------------------------------------------------------------------
# 3. Dimension: Agents (3 teams)
# ----------------------------------------------------------------------
FIRST_NAMES = ["Aarav","Vivaan","Aditya","Ananya","Diya","Ishaan","Kabir","Meera",
               "Neha","Om","Pooja","Rohan","Sana","Tara","Uday","Varun","Yash",
               "Zara","Kavya","Arjun","Priya","Rahul","Sneha","Karan","Isha"]
TEAMS = ["Tier-1 Support", "Fraud & Disputes", "Technical Escalations"]

n_agents = 24
agents = pd.DataFrame({
    "agent_id": range(1, n_agents + 1),
    "agent_name": [f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {chr(65 + (i * 7) % 26)}." for i in range(n_agents)],
    "team": [TEAMS[i % 3] for i in range(n_agents)],
})

# ----------------------------------------------------------------------
# 4. Simulate "incident days" - real app outages / bad releases
#    These days cause a big spike in Technical + Failed-Transaction
#    complaints, which we deliberately use later for root-cause analysis.
# ----------------------------------------------------------------------
incident_days = [
    datetime(2025, 10, 14),   # simulated bad app release
    datetime(2026, 1, 5),     # simulated NPCI switch outage (new year traffic)
    datetime(2026, 5, 22),    # simulated server outage
]

# ----------------------------------------------------------------------
# 5. Decide daily ticket volume per day (seasonality + growth + incidents)
# ----------------------------------------------------------------------
dates = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
daily_volumes = []
base_volume = 32

for i, d in enumerate(dates):
    growth_factor = 1 + (i / TOTAL_DAYS) * 0.5          # ~50% organic growth over the year
    salary_spike = 1.4 if d.day in (1, 2, 25, 26, 27, 28, 29, 30, 31) else 1.0
    weekend_dip = 0.85 if d.weekday() >= 5 else 1.0
    incident_spike = 3.2 if any(d.date() == inc.date() for inc in incident_days) else 1.0
    noise = rng.normal(1.0, 0.08)

    vol = base_volume * growth_factor * salary_spike * weekend_dip * incident_spike * noise
    daily_volumes.append(max(5, int(round(vol))))

total_tickets = sum(daily_volumes)
print(f"Planned total tickets: {total_tickets}")

# ----------------------------------------------------------------------
# 6. Generate each ticket
# ----------------------------------------------------------------------
records = []
ticket_id = 100000

cat_ids = categories["category_id"].values
cat_weights = categories["base_weight"].values
cat_weights = cat_weights / cat_weights.sum()
cat_sla = dict(zip(categories.category_id, categories.sla_target_hours))
cat_group = dict(zip(categories.category_id, categories.category_group))

for d, vol in zip(dates, daily_volumes):
    is_incident_day = any(d.date() == inc.date() for inc in incident_days)

    for _ in range(vol):
        # On incident days, heavily bias toward Technical (8) and Failed Transaction (1)
        if is_incident_day and rng.random() < 0.75:
            category_id = rng.choice([1, 8], p=[0.55, 0.45])
        else:
            category_id = rng.choice(cat_ids, p=cat_weights)

        channel_id = rng.choice(channels.channel_id.values, p=[0.32, 0.28, 0.12, 0.16, 0.12])

        # Assign agent based on category group (route to the right team)
        group = cat_group[category_id]
        if group == "Fraud & Disputes":
            pool = agents[agents.team == "Fraud & Disputes"].agent_id.values
        elif group == "Technical":
            pool = agents[agents.team == "Technical Escalations"].agent_id.values
        else:
            pool = agents[agents.team == "Tier-1 Support"].agent_id.values
        agent_id = rng.choice(pool)

        # Random time-of-day, weighted toward business hours
        hour = int(np.clip(rng.normal(14, 4), 0, 23))
        minute = rng.integers(0, 60)
        opened_at = d.replace(hour=hour, minute=int(minute), second=int(rng.integers(0, 60)))

        sla_target = cat_sla[category_id]

        # Resolution time: lognormal centered near the SLA target.
        # Fraud/dispute cases have a fatter right tail (many breach SLA).
        if group == "Fraud & Disputes":
            mu = np.log(sla_target * 0.9)
            sigma = 0.55
        elif group == "Technical":
            mu = np.log(sla_target * 0.5)
            sigma = 0.45
        else:
            mu = np.log(sla_target * 0.7)
            sigma = 0.5

        resolution_hours = float(rng.lognormal(mu, sigma))
        resolution_hours = round(min(resolution_hours, sla_target * 6), 2)  # cap extreme outliers

        closed_at = opened_at + timedelta(hours=resolution_hours)

        # Tickets opened in the last 5 days may still be open (unresolved)
        days_since_open = (END_DATE - d).days
        if days_since_open <= 5 and rng.random() < 0.35:
            status = "Open"
            closed_at = pd.NaT
            resolution_hours = np.nan
            sla_breached = (END_DATE - opened_at).total_seconds() / 3600 > sla_target
        else:
            status = "Closed"
            sla_breached = resolution_hours > sla_target

        root_cause = rng.choice(ROOT_CAUSES[category_id]) if status == "Closed" else None

        transaction_amount = round(float(rng.lognormal(mean=6.5, sigma=1.1)), 2)  # skewed, in INR
        transaction_amount = min(transaction_amount, 200000)

        customer_id = f"CUST{rng.integers(100000, 999999)}"

        records.append((
            ticket_id, customer_id, category_id, channel_id, agent_id,
            round(transaction_amount, 2), opened_at, closed_at, status,
            resolution_hours, sla_target, bool(sla_breached), root_cause,
            is_incident_day,
        ))
        ticket_id += 1

fact_complaints = pd.DataFrame(records, columns=[
    "ticket_id", "customer_id", "category_id", "channel_id", "agent_id",
    "transaction_amount_inr", "opened_at", "closed_at", "status",
    "resolution_hours", "sla_target_hours", "sla_breached", "root_cause",
    "is_incident_day",
])

# ----------------------------------------------------------------------
# 7. Deliberately introduce realistic messiness, exactly like real
#    exported support-ticket data (mixed timestamp formats, a few
#    duplicate rows, a few missing agent assignments). The Uber project
#    on this resume already proves the cleaning skill; this proves it
#    again on a second, different data-quality problem set.
# ----------------------------------------------------------------------
messy = fact_complaints.copy()

# 7a. Mixed timestamp string formats for a random subset (simulates
#     different export tools / locales)
def messy_timestamp(ts):
    if pd.isna(ts):
        return ts
    fmt_choice = rng.integers(0, 4)
    if fmt_choice == 0:
        return ts.strftime("%Y-%m-%d %H:%M:%S")          # ISO-like
    elif fmt_choice == 1:
        return ts.strftime("%d/%m/%Y %H:%M")              # DD/MM/YYYY
    elif fmt_choice == 2:
        return ts.strftime("%m-%d-%Y %I:%M %p")            # US-style
    else:
        return ts.strftime("%d-%b-%Y %H:%M:%S")            # 30-Jul-2026

messy["opened_at"] = messy["opened_at"].apply(messy_timestamp)
messy["closed_at"] = messy["closed_at"].apply(messy_timestamp)

# 7b. Inject ~40 duplicate rows (simulates double-submitted tickets)
dupe_rows = messy.sample(n=40, random_state=SEED)
messy = pd.concat([messy, dupe_rows], ignore_index=True)

# 7c. Null out ~1.5% of agent_id (simulates unassigned tickets in the raw export)
null_idx = messy.sample(frac=0.015, random_state=SEED).index
messy.loc[null_idx, "agent_id"] = np.nan

# 7d. A handful of stray whitespace / casing issues in customer_id
whitespace_idx = messy.sample(frac=0.01, random_state=SEED + 1).index
messy.loc[whitespace_idx, "customer_id"] = messy.loc[whitespace_idx, "customer_id"].apply(lambda x: f"  {x.lower()} ")

# ----------------------------------------------------------------------
# 8. Save outputs
# ----------------------------------------------------------------------
categories.drop(columns=["base_weight"]).to_csv(DATA_DIR / "dim_category.csv", index=False)
channels.to_csv(DATA_DIR / "dim_channel.csv", index=False)
agents.to_csv(DATA_DIR / "dim_agent.csv", index=False)
messy.to_csv(DATA_DIR / "fact_complaints_raw.csv", index=False)          # the "messy" raw export
fact_complaints.to_csv(DATA_DIR / "fact_complaints_clean_reference.csv", index=False)  # ground truth, for validation only

print(f"Generated {len(fact_complaints):,} clean tickets, exported as {len(messy):,} raw/messy rows.")
print(f"Incident days simulated: {[d.strftime('%Y-%m-%d') for d in incident_days]}")
print("Files written to:", DATA_DIR)
