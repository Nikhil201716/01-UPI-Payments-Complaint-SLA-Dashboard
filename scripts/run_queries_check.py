"""Quick verification runner: executes every query in sql/analysis_queries.sql
against the built database and prints results, so we can both (a) confirm the
SQL file has no syntax errors and (b) pull real numbers for the written
root-cause analysis report and README."""
import re
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "complaints.db"
SQL_PATH = ROOT / "sql" / "analysis_queries.sql"

conn = sqlite3.connect(DB_PATH)
raw = SQL_PATH.read_text(encoding="utf-8")

blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]

LABEL_RE = re.compile(r"^--\s*([A-E]\d+\.\s.+)$")

count = 0
for block in blocks:
    lines = block.split("\n")
    label = None
    sql_lines = []
    for line in lines:
        m = LABEL_RE.match(line.strip())
        if m:
            label = m.group(1)
        elif not line.strip().startswith("--"):
            sql_lines.append(line)
    sql = "\n".join(sql_lines).strip().rstrip(";")
    if not sql:
        continue
    try:
        df = pd.read_sql_query(sql, conn)
        count += 1
        print(f"\n=== {label or '(unlabeled query)'} ===")
        print(df.to_string(index=False))
    except Exception as e:
        print(f"\n!!! FAILED: {label}\n{sql}\nError: {e}")

print(f"\n\nTotal queries executed successfully: {count}")
conn.close()
