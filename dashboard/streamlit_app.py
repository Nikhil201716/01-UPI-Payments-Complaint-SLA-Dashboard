"""
streamlit_app.py
-----------------
Interactive web dashboard for the UPI Payments Complaint & SLA Analytics
project. Reads directly from the SQLite database and lets a support-ops
stakeholder filter by date range, category, and channel to instantly see
SLA compliance, resolution-time trends, and root-cause breakdowns.

Run with:
    streamlit run dashboard/streamlit_app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "complaints.db"

st.set_page_config(page_title="UPI Complaint & SLA Dashboard", layout="wide", page_icon="📊")


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT f.ticket_id, f.customer_id, c.category_name, c.category_group,
               ch.channel_name, a.agent_name, a.team, f.transaction_amount_inr,
               f.opened_at, f.closed_at, f.status, f.resolution_hours,
               f.sla_target_hours, f.sla_breached, f.root_cause, f.is_incident_day
        FROM fact_complaints f
        JOIN dim_category c ON f.category_id = c.category_id
        JOIN dim_channel ch ON f.channel_id = ch.channel_id
        JOIN dim_agent a ON f.agent_id = a.agent_id
    """, conn)
    conn.close()
    df["opened_at"] = pd.to_datetime(df["opened_at"])
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    return df


df = load_data()

# ------------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------------
st.sidebar.title("Filters")

min_date, max_date = df["opened_at"].min().date(), df["opened_at"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)

categories = sorted(df["category_name"].unique())
selected_categories = st.sidebar.multiselect("Complaint category", categories, default=categories)

channels = sorted(df["channel_name"].unique())
selected_channels = st.sidebar.multiselect("Channel", channels, default=channels)

incident_only = st.sidebar.checkbox("Show incident days only", value=False)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask = (
    (df["opened_at"].dt.date >= start_date)
    & (df["opened_at"].dt.date <= end_date)
    & (df["category_name"].isin(selected_categories))
    & (df["channel_name"].isin(selected_channels))
)
if incident_only:
    mask &= df["is_incident_day"] == 1

fdf = df[mask]

# ------------------------------------------------------------------
# Header + KPI cards
# ------------------------------------------------------------------
st.title("📊 UPI Digital Payments — Complaint & SLA Analytics")
st.caption("Synthetic support-ticket data modeled on RBI digital-payment complaint categories and "
           "real fintech customer-support operational patterns. All data is synthetically generated.")

total_tickets = len(fdf)
closed = fdf[fdf.status == "Closed"]
sla_compliance = 100 * (1 - fdf["sla_breached"].mean()) if total_tickets else 0
avg_resolution = closed["resolution_hours"].mean() if len(closed) else 0
open_tickets = (fdf.status == "Open").sum()
disputed_value = fdf["transaction_amount_inr"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Tickets", f"{total_tickets:,}")
k2.metric("SLA Compliance", f"{sla_compliance:.1f}%")
k3.metric("Avg Resolution", f"{avg_resolution:.1f} hrs")
k4.metric("Open Tickets", f"{open_tickets:,}")
k5.metric("Disputed Value", f"₹{disputed_value:,.0f}")

st.divider()

# ------------------------------------------------------------------
# Row 1: SLA breach by category  |  Monthly trend
# ------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("SLA Breach % by Category")
    cat_summary = (
        fdf.groupby("category_name")
        .agg(tickets=("ticket_id", "count"), sla_breach_pct=("sla_breached", lambda x: 100 * x.mean()))
        .reset_index()
        .sort_values("sla_breach_pct", ascending=False)
    )
    fig1 = px.bar(cat_summary, x="sla_breach_pct", y="category_name", orientation="h",
                   color="sla_breach_pct", color_continuous_scale="RdYlGn_r",
                   labels={"sla_breach_pct": "SLA Breach %", "category_name": ""})
    fig1.update_layout(height=430, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    st.subheader("Monthly Volume & SLA Compliance")
    fdf["month"] = fdf["opened_at"].dt.to_period("M").astype(str)
    monthly = (
        fdf.groupby("month")
        .agg(tickets=("ticket_id", "count"), sla_compliance_pct=("sla_breached", lambda x: 100 * (1 - x.mean())))
        .reset_index()
    )
    fig2 = px.bar(monthly, x="month", y="tickets", labels={"tickets": "Tickets", "month": ""})
    fig2b = px.line(monthly, x="month", y="sla_compliance_pct")
    fig2b.update_traces(yaxis="y2", line=dict(color="#2E6F40", width=3))
    fig2.add_trace(fig2b.data[0])
    fig2.update_layout(
        height=430,
        yaxis2=dict(overlaying="y", side="right", title="SLA Compliance %", range=[0, 100]),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# Row 2: Channel breakdown  |  Root cause breakdown
# ------------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.subheader("Tickets by Channel")
    chan_summary = fdf.groupby("channel_name").size().reset_index(name="tickets")
    fig3 = px.pie(chan_summary, names="channel_name", values="tickets", hole=0.45)
    fig3.update_layout(height=400)
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("Top Root Causes (SLA-Breached Tickets)")
    breached = fdf[fdf.sla_breached == 1]
    rc = breached["root_cause"].value_counts().head(8).reset_index()
    rc.columns = ["root_cause", "breached_tickets"]
    fig4 = px.bar(rc, x="breached_tickets", y="root_cause", orientation="h",
                   labels={"breached_tickets": "Breached Tickets", "root_cause": ""})
    fig4.update_layout(height=400, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Drill-through table
# ------------------------------------------------------------------
st.subheader("Drill-Through: Ticket Detail")
st.caption(f"Showing {len(fdf):,} tickets matching the current filters.")
show_cols = ["ticket_id", "customer_id", "category_name", "channel_name", "team", "agent_name",
             "opened_at", "status", "resolution_hours", "sla_target_hours", "sla_breached", "root_cause"]
st.dataframe(fdf[show_cols].sort_values("opened_at", ascending=False), use_container_width=True, height=350)

csv = fdf[show_cols].to_csv(index=False).encode("utf-8")
st.download_button("Download filtered data as CSV", csv, "filtered_complaints.csv", "text/csv")
