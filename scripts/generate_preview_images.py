"""
generate_preview_images.py
---------------------------
Renders static PNG preview charts (matplotlib/seaborn) straight from the
database, for the README/GitHub repo. These are NOT literal screenshots of
the Streamlit app (this environment has no display to screenshot) - they
are real charts built from the same underlying data the Streamlit app and
Excel dashboard both use, so the numbers are identical.

Output: ../screenshots/*.png
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "complaints.db"
OUT_DIR = ROOT / "screenshots"
OUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid")
NAVY = "#1F3A5F"
ACCENT = "#2E6F40"
RED = "#C0392B"

conn = sqlite3.connect(DB_PATH)

# ------------------------------------------------------------------
# 1. KPI summary card (rendered as a simple figure)
# ------------------------------------------------------------------
kpi = pd.read_sql_query("""
    SELECT COUNT(*) AS total_tickets,
           ROUND(100.0*SUM(CASE WHEN sla_breached=0 THEN 1 ELSE 0 END)/COUNT(*),1) AS sla_compliance_pct,
           ROUND(AVG(resolution_hours),1) AS avg_resolution_hours,
           SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END) AS open_tickets,
           ROUND(SUM(transaction_amount_inr),0) AS disputed_value
    FROM fact_complaints
""", conn).iloc[0]

fig, axes = plt.subplots(1, 5, figsize=(16, 2.2))
cards = [
    ("Total Tickets", f"{int(kpi.total_tickets):,}"),
    ("SLA Compliance", f"{kpi.sla_compliance_pct}%"),
    ("Avg Resolution", f"{kpi.avg_resolution_hours} hrs"),
    ("Open Tickets", f"{int(kpi.open_tickets):,}"),
    ("Disputed Value", f"Rs {kpi.disputed_value/1e7:.2f} Cr"),
]
for ax, (label, value) in zip(axes, cards):
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color=NAVY, transform=ax.transAxes, zorder=0))
    ax.text(0.5, 0.68, label, ha="center", va="center", color="white", fontsize=10, transform=ax.transAxes)
    ax.text(0.5, 0.32, value, ha="center", va="center", color="white", fontsize=15, fontweight="bold", transform=ax.transAxes)
fig.suptitle("UPI Complaint & SLA Dashboard - Key Metrics (12-Month View)", fontsize=12, color=NAVY, y=1.05)
plt.tight_layout()
plt.savefig(OUT_DIR / "01_kpi_summary.png", dpi=150, bbox_inches="tight")
plt.close()

# ------------------------------------------------------------------
# 2. SLA breach % by category (horizontal bar, colour-scaled)
# ------------------------------------------------------------------
by_cat = pd.read_sql_query("""
    SELECT c.category_name, ROUND(100.0*SUM(f.sla_breached)/COUNT(*),1) AS breach_pct, COUNT(*) AS tickets
    FROM fact_complaints f JOIN dim_category c ON f.category_id=c.category_id
    GROUP BY c.category_name ORDER BY breach_pct ASC
""", conn)

fig, ax = plt.subplots(figsize=(9, 5.5))
colors = sns.color_palette("RdYlGn_r", n_colors=len(by_cat))
bars = ax.barh(by_cat.category_name, by_cat.breach_pct, color=colors)
for bar, pct in zip(bars, by_cat.breach_pct):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, f"{pct}%", va="center", fontsize=9)
ax.set_xlabel("SLA Breach %")
ax.set_title("SLA Breach % by Complaint Category", color=NAVY, fontsize=13, fontweight="bold")
ax.set_xlim(0, 50)
plt.tight_layout()
plt.savefig(OUT_DIR / "02_sla_breach_by_category.png", dpi=150, bbox_inches="tight")
plt.close()

# ------------------------------------------------------------------
# 3. Monthly volume + SLA compliance trend (dual axis)
# ------------------------------------------------------------------
monthly = pd.read_sql_query("""
    SELECT strftime('%Y-%m', opened_at) AS month, COUNT(*) AS tickets,
           ROUND(100.0*SUM(CASE WHEN sla_breached=0 THEN 1 ELSE 0 END)/COUNT(*),1) AS sla_pct
    FROM fact_complaints GROUP BY month ORDER BY month
""", conn)

fig, ax1 = plt.subplots(figsize=(10, 4.5))
ax1.bar(monthly.month, monthly.tickets, color=NAVY, alpha=0.75, label="Ticket Volume")
ax1.set_ylabel("Tickets")
ax1.set_xticklabels(monthly.month, rotation=45, ha="right")
ax2 = ax1.twinx()
ax2.plot(monthly.month, monthly.sla_pct, color=ACCENT, marker="o", linewidth=2.5, label="SLA Compliance %")
ax2.set_ylabel("SLA Compliance %")
ax2.set_ylim(0, 100)
fig.suptitle("Monthly Ticket Volume vs. SLA Compliance", color=NAVY, fontsize=13, fontweight="bold")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
plt.tight_layout()
plt.savefig(OUT_DIR / "03_monthly_trend.png", dpi=150, bbox_inches="tight")
plt.close()

# ------------------------------------------------------------------
# 4. Top root causes of SLA-breached tickets
# ------------------------------------------------------------------
rc = pd.read_sql_query("""
    SELECT root_cause, COUNT(*) AS breached_tickets
    FROM fact_complaints WHERE sla_breached=1 AND root_cause IS NOT NULL
    GROUP BY root_cause ORDER BY breached_tickets DESC LIMIT 8
""", conn).sort_values("breached_tickets")

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.barh(rc.root_cause, rc.breached_tickets, color=RED, alpha=0.85)
ax.set_xlabel("Breached Tickets")
ax.set_title("Top 8 Root Causes of SLA-Breached Tickets", color=NAVY, fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(OUT_DIR / "04_top_root_causes.png", dpi=150, bbox_inches="tight")
plt.close()

# ------------------------------------------------------------------
# 5. Incident-day vs normal-day comparison
# ------------------------------------------------------------------
inc = pd.read_sql_query("""
    SELECT CASE WHEN is_incident_day=1 THEN 'Incident Days (3)' ELSE 'Normal Days (361)' END AS day_type,
           ROUND(COUNT(*)*1.0/COUNT(DISTINCT date(opened_at)),1) AS avg_tickets_per_day,
           ROUND(100.0*SUM(sla_breached)/COUNT(*),1) AS sla_breach_pct
    FROM fact_complaints GROUP BY is_incident_day
""", conn)

fig, axes = plt.subplots(1, 2, figsize=(9, 4))
axes[0].bar(inc.day_type, inc.avg_tickets_per_day, color=[NAVY, RED])
axes[0].set_title("Avg Tickets / Day")
axes[1].bar(inc.day_type, inc.sla_breach_pct, color=[NAVY, RED])
axes[1].set_title("SLA Breach %")
for ax in axes:
    ax.tick_params(axis="x", rotation=15)
fig.suptitle("Incident Days: High Volume, But Not the Worst SLA Offender", color=NAVY, fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(OUT_DIR / "05_incident_day_comparison.png", dpi=150, bbox_inches="tight")
plt.close()

conn.close()
print("Saved 5 preview images to", OUT_DIR)
