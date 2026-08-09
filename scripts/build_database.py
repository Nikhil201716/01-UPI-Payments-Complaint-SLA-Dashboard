"""
build_database.py
------------------
Creates the normalized SQLite database (database/complaints.db) from:
  - sql/schema.sql            (table definitions)
  - data/dim_category.csv
  - data/dim_channel.csv
  - data/dim_agent.csv
  - data/fact_complaints_clean.csv

Run this AFTER generate_data.py and clean_transform.py.
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "database" / "complaints.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

DB_PATH.parent.mkdir(exist_ok=True)

# Fresh build every run
if DB_PATH.exists():
    DB_PATH.unlink()

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. Create schema
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    cur.executescript(f.read())
print("Schema created.")

# 2. Add an "Unassigned" placeholder agent for tickets with agent_id = -1
cur.execute("INSERT INTO dim_agent (agent_id, agent_name, team) VALUES (-1, 'Unassigned', 'Unassigned')")

# 3. Load dimension tables
dim_category = pd.read_csv(DATA_DIR / "dim_category.csv")
dim_channel = pd.read_csv(DATA_DIR / "dim_channel.csv")
dim_agent = pd.read_csv(DATA_DIR / "dim_agent.csv")

dim_category.to_sql("dim_category", conn, if_exists="append", index=False)
dim_channel.to_sql("dim_channel", conn, if_exists="append", index=False)
dim_agent.to_sql("dim_agent", conn, if_exists="append", index=False)
print(f"Loaded {len(dim_category)} categories, {len(dim_channel)} channels, {len(dim_agent)} agents.")

# 4. Load the fact table
fact = pd.read_csv(DATA_DIR / "fact_complaints_clean.csv")
fact.to_sql("fact_complaints", conn, if_exists="append", index=False)
print(f"Loaded {len(fact):,} complaint tickets into fact_complaints.")

conn.commit()

# 5. Sanity check: row counts + a quick preview query
check = pd.read_sql_query("""
    SELECT c.category_name, COUNT(*) AS tickets, ROUND(AVG(f.resolution_hours), 1) AS avg_resolution_hrs,
           ROUND(100.0 * SUM(f.sla_breached) / COUNT(*), 1) AS sla_breach_pct
    FROM fact_complaints f
    JOIN dim_category c ON f.category_id = c.category_id
    GROUP BY c.category_name
    ORDER BY sla_breach_pct DESC
""", conn)
print("\nQuick sanity check - SLA breach % by category:\n")
print(check.to_string(index=False))

conn.close()
print(f"\nDatabase built at: {DB_PATH}")
