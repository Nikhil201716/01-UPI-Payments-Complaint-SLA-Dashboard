"""
run_pipeline.py
----------------
One-command orchestrator for the full ETL pipeline. Running this single
script regenerates everything downstream from one source of truth -
synthetic data -> cleaned data -> SQLite database -> Excel dashboard -
so nothing ever has to be manually re-entered across systems.

Usage:
    python scripts/run_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent

STEPS = [
    ("Generating synthetic complaint data", SCRIPTS_DIR / "generate_data.py"),
    ("Cleaning & transforming raw data", SCRIPTS_DIR / "clean_transform.py"),
    ("Building SQLite database", SCRIPTS_DIR / "build_database.py"),
    ("Validating SQL analysis queries", SCRIPTS_DIR / "run_queries_check.py"),
    ("Building Excel dashboard", ROOT / "dashboard" / "build_excel_dashboard.py"),
]

for i, (label, script) in enumerate(STEPS, start=1):
    print(f"\n{'=' * 70}\nSTEP {i}/{len(STEPS)}: {label}\n{'=' * 70}")
    result = subprocess.run([sys.executable, str(script)], cwd=script.parent)
    if result.returncode != 0:
        print(f"\nPipeline FAILED at step {i}: {label}")
        sys.exit(1)

print(f"\n{'=' * 70}\nPipeline completed successfully.")
print("Next: run the interactive dashboard with:")
print("    streamlit run dashboard/streamlit_app.py")
print(f"{'=' * 70}")
