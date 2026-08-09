"""
clean_transform.py
-------------------
Takes the deliberately messy raw export (fact_complaints_raw.csv, which has
mixed timestamp formats, duplicate rows, missing agent assignments, and
stray whitespace/casing issues - exactly like a real ticketing-system
export) and produces a single clean, analysis-ready CSV.

This is the same "standardize mixed-format timestamps to ISO 8601" skill
used on the Uber Supply-Demand Gap Analysis project, applied here to a
second, independent messy dataset.

Input:  ../data/fact_complaints_raw.csv
Output: ../data/fact_complaints_clean.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

raw = pd.read_csv(DATA_DIR / "fact_complaints_raw.csv")
print(f"Raw rows loaded: {len(raw):,}")

# ------------------------------------------------------------------
# 1. Standardize mixed-format timestamps to ISO 8601 (YYYY-MM-DD HH:MM:SS)
#    The raw file mixes 4 different formats across rows on purpose.
# ------------------------------------------------------------------
TS_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m-%d-%Y %I:%M %p",
    "%d-%b-%Y %H:%M:%S",
]

def parse_mixed_timestamp(value):
    if pd.isna(value):
        return pd.NaT
    value = str(value).strip()
    for fmt in TS_FORMATS:
        try:
            return pd.to_datetime(value, format=fmt)
        except (ValueError, TypeError):
            continue
    # last resort: let pandas guess
    return pd.to_datetime(value, errors="coerce")

for col in ["opened_at", "closed_at"]:
    raw[col] = raw[col].apply(parse_mixed_timestamp)

unparsed = raw["opened_at"].isna().sum()
print(f"Rows where opened_at failed to parse: {unparsed}")

# ------------------------------------------------------------------
# 2. Remove exact duplicate tickets (simulated double-submitted rows)
# ------------------------------------------------------------------
before = len(raw)
raw = raw.drop_duplicates(subset=["ticket_id"], keep="first")
print(f"Removed {before - len(raw):,} duplicate ticket rows")

# ------------------------------------------------------------------
# 3. Normalize customer_id (trim whitespace, consistent casing)
# ------------------------------------------------------------------
raw["customer_id"] = raw["customer_id"].str.strip().str.upper()

# ------------------------------------------------------------------
# 4. Handle missing agent_id: route to a placeholder "Unassigned" bucket
#    (agent_id = -1) rather than silently dropping the row - dropping
#    real complaint rows would understate ticket volume.
# ------------------------------------------------------------------
raw["agent_id"] = raw["agent_id"].fillna(-1).astype(int)

# ------------------------------------------------------------------
# 5. Recompute / validate resolution_hours and sla_breached from the
#    now-clean timestamps, rather than trusting the raw export blindly.
# ------------------------------------------------------------------
now_ceiling = pd.Timestamp("2026-07-30 23:59:59")

def compute_resolution(row):
    if row["status"] == "Closed" and pd.notna(row["closed_at"]):
        return (row["closed_at"] - row["opened_at"]).total_seconds() / 3600
    return np.nan

raw["resolution_hours"] = raw.apply(compute_resolution, axis=1).round(2)

def compute_breach(row):
    if row["status"] == "Closed":
        return row["resolution_hours"] > row["sla_target_hours"]
    else:
        elapsed = (now_ceiling - row["opened_at"]).total_seconds() / 3600
        return elapsed > row["sla_target_hours"]

raw["sla_breached"] = raw.apply(compute_breach, axis=1).astype(int)

# ------------------------------------------------------------------
# 6. Format timestamps back out as clean ISO 8601 strings for storage
# ------------------------------------------------------------------
raw["opened_at"] = raw["opened_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
raw["closed_at"] = raw["closed_at"].dt.strftime("%Y-%m-%d %H:%M:%S")

# ------------------------------------------------------------------
# 7. Basic data-quality assertions before saving (fail loudly, not silently)
# ------------------------------------------------------------------
assert raw["ticket_id"].is_unique, "Duplicate ticket_id survived cleaning!"
assert raw["opened_at"].notna().all(), "Some opened_at timestamps are still null!"
assert raw["status"].isin(["Open", "Closed"]).all(), "Unexpected status value found!"

cols = [
    "ticket_id", "customer_id", "category_id", "channel_id", "agent_id",
    "transaction_amount_inr", "opened_at", "closed_at", "status",
    "resolution_hours", "sla_target_hours", "sla_breached", "root_cause",
    "is_incident_day",
]
clean = raw[cols].sort_values("ticket_id").reset_index(drop=True)
clean.to_csv(DATA_DIR / "fact_complaints_clean.csv", index=False)

print(f"Clean rows saved: {len(clean):,}")
print("Saved to:", DATA_DIR / "fact_complaints_clean.csv")
