-- ============================================================================
-- analysis_queries.sql
-- 18 analytical queries answering the real operational questions a digital
-- payments support/ops leader would ask about their complaint queue.
-- Run against database/complaints.db (SQLite).
--
-- Grouped into 5 sections:
--   A. Overall KPIs
--   B. SLA breach analysis (root-cause driving questions)
--   C. Volume & trend analysis
--   D. Channel & agent performance
--   E. Incident-day deep dive
-- ============================================================================


-- ============================================================================
-- SECTION A: OVERALL KPIs
-- ============================================================================

-- A1. Headline KPIs: total tickets, % closed, overall SLA compliance rate
SELECT
    COUNT(*)                                                   AS total_tickets,
    SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END)         AS closed_tickets,
    SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END)           AS open_tickets,
    ROUND(100.0 * SUM(CASE WHEN sla_breached = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS sla_compliance_pct,
    ROUND(AVG(resolution_hours), 1)                            AS avg_resolution_hours
FROM fact_complaints;

-- A2. Average resolution time overall vs. median (shows skew from long-tail cases)
SELECT
    ROUND(AVG(resolution_hours), 1) AS mean_resolution_hours,
    (SELECT resolution_hours FROM fact_complaints
     WHERE resolution_hours IS NOT NULL
     ORDER BY resolution_hours
     LIMIT 1
     OFFSET (SELECT COUNT(*) FROM fact_complaints WHERE resolution_hours IS NOT NULL) / 2
    ) AS median_resolution_hours
FROM fact_complaints;

-- A3. Total transaction value represented by complaints (business exposure)
SELECT
    ROUND(SUM(transaction_amount_inr), 2) AS total_disputed_value_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS avg_transaction_value_inr
FROM fact_complaints;


-- ============================================================================
-- SECTION B: SLA BREACH ANALYSIS (root-cause driving questions)
-- ============================================================================

-- B1. SLA breach rate and volume by category, ranked worst-first
SELECT
    c.category_name,
    c.category_group,
    c.sla_target_hours,
    COUNT(*)                                                    AS ticket_count,
    ROUND(AVG(f.resolution_hours), 1)                           AS avg_resolution_hours,
    ROUND(100.0 * SUM(f.sla_breached) / COUNT(*), 1)            AS sla_breach_pct
FROM fact_complaints f
JOIN dim_category c ON f.category_id = c.category_id
GROUP BY c.category_name, c.category_group, c.sla_target_hours
ORDER BY sla_breach_pct DESC;

-- B2. SLA breach rate by category GROUP (higher-level rollup for executives)
SELECT
    c.category_group,
    COUNT(*)                                          AS ticket_count,
    ROUND(100.0 * SUM(f.sla_breached) / COUNT(*), 1)  AS sla_breach_pct
FROM fact_complaints f
JOIN dim_category c ON f.category_id = c.category_id
GROUP BY c.category_group
ORDER BY sla_breach_pct DESC;

-- B3. Top 10 root causes contributing the most SLA-breached tickets
SELECT
    root_cause,
    COUNT(*) AS breached_tickets
FROM fact_complaints
WHERE sla_breached = 1 AND root_cause IS NOT NULL
GROUP BY root_cause
ORDER BY breached_tickets DESC
LIMIT 10;

-- B4. Resolution time distribution buckets (helps spot long-tail problem cases)
SELECT
    CASE
        WHEN resolution_hours <= 24  THEN '0-24 hrs'
        WHEN resolution_hours <= 48  THEN '24-48 hrs'
        WHEN resolution_hours <= 72  THEN '48-72 hrs'
        WHEN resolution_hours <= 168 THEN '72-168 hrs'
        ELSE '168+ hrs'
    END AS resolution_bucket,
    COUNT(*) AS ticket_count
FROM fact_complaints
WHERE status = 'Closed'
GROUP BY resolution_bucket
ORDER BY MIN(resolution_hours);

-- B5. Which category group has the highest disputed transaction VALUE at risk
--     from SLA-breached tickets (ties breach rate to real business dollars)
SELECT
    c.category_group,
    COUNT(*) AS breached_tickets,
    ROUND(SUM(f.transaction_amount_inr), 2) AS disputed_value_inr
FROM fact_complaints f
JOIN dim_category c ON f.category_id = c.category_id
WHERE f.sla_breached = 1
GROUP BY c.category_group
ORDER BY disputed_value_inr DESC;


-- ============================================================================
-- SECTION C: VOLUME & TREND ANALYSIS
-- ============================================================================

-- C1. Monthly ticket volume trend (is the complaint load growing?)
SELECT
    strftime('%Y-%m', opened_at) AS month,
    COUNT(*) AS ticket_count
FROM fact_complaints
GROUP BY month
ORDER BY month;

-- C2. Monthly SLA compliance trend (is quality improving or degrading over time?)
SELECT
    strftime('%Y-%m', opened_at) AS month,
    COUNT(*) AS ticket_count,
    ROUND(100.0 * SUM(CASE WHEN sla_breached = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS sla_compliance_pct
FROM fact_complaints
GROUP BY month
ORDER BY month;

-- C3. Day-of-week volume pattern (staffing planning input)
SELECT
    CASE CAST(strftime('%w', opened_at) AS INTEGER)
        WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
        ELSE 'Saturday'
    END AS day_of_week,
    COUNT(*) AS ticket_count
FROM fact_complaints
GROUP BY strftime('%w', opened_at)
ORDER BY strftime('%w', opened_at);

-- C4. "Salary-date" spike check: complaints on day-of-month 25-31 or 1-2
--     vs. all other days (validates a real, well-known fintech ops pattern)
SELECT
    CASE
        WHEN CAST(strftime('%d', opened_at) AS INTEGER) >= 25
          OR CAST(strftime('%d', opened_at) AS INTEGER) <= 2
        THEN 'Salary-date window'
        ELSE 'Rest of month'
    END AS period,
    COUNT(*) AS ticket_count,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT date(opened_at)), 1) AS avg_tickets_per_day
FROM fact_complaints
GROUP BY period;


-- ============================================================================
-- SECTION D: CHANNEL & AGENT PERFORMANCE
-- ============================================================================

-- D1. SLA breach rate and volume by payment channel
SELECT
    ch.channel_name,
    COUNT(*) AS ticket_count,
    ROUND(100.0 * SUM(f.sla_breached) / COUNT(*), 1) AS sla_breach_pct
FROM fact_complaints f
JOIN dim_channel ch ON f.channel_id = ch.channel_id
GROUP BY ch.channel_name
ORDER BY sla_breach_pct DESC;

-- D2. Team-level performance (Tier-1 vs. Fraud & Disputes vs. Technical Escalations)
SELECT
    a.team,
    COUNT(*) AS ticket_count,
    ROUND(AVG(f.resolution_hours), 1) AS avg_resolution_hours,
    ROUND(100.0 * SUM(f.sla_breached) / COUNT(*), 1) AS sla_breach_pct
FROM fact_complaints f
JOIN dim_agent a ON f.agent_id = a.agent_id
GROUP BY a.team
ORDER BY sla_breach_pct DESC;

-- D3. Top 5 individual agents by ticket volume handled (workload distribution check)
SELECT
    a.agent_name,
    a.team,
    COUNT(*) AS tickets_handled,
    ROUND(100.0 * SUM(f.sla_breached) / COUNT(*), 1) AS sla_breach_pct
FROM fact_complaints f
JOIN dim_agent a ON f.agent_id = a.agent_id
WHERE a.agent_id != -1
GROUP BY a.agent_name, a.team
ORDER BY tickets_handled DESC
LIMIT 5;

-- D4. Unassigned ticket count (a process/data-quality gap worth flagging)
SELECT COUNT(*) AS unassigned_tickets
FROM fact_complaints
WHERE agent_id = -1;


-- ============================================================================
-- SECTION E: INCIDENT-DAY DEEP DIVE
-- ============================================================================

-- E1. Confirm the incident-day volume spike vs. normal days
SELECT
    is_incident_day,
    COUNT(DISTINCT date(opened_at)) AS days_counted,
    COUNT(*) AS total_tickets,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT date(opened_at)), 1) AS avg_tickets_per_day
FROM fact_complaints
GROUP BY is_incident_day;

-- E2. Which categories spiked hardest on incident days specifically
SELECT
    c.category_name,
    COUNT(*) AS tickets_on_incident_days
FROM fact_complaints f
JOIN dim_category c ON f.category_id = c.category_id
WHERE f.is_incident_day = 1
GROUP BY c.category_name
ORDER BY tickets_on_incident_days DESC
LIMIT 5;

-- E3. SLA breach rate specifically on incident days vs. normal days
--     (proves incidents don't just create volume - they also break SLAs)
SELECT
    is_incident_day,
    COUNT(*) AS ticket_count,
    ROUND(100.0 * SUM(sla_breached) / COUNT(*), 1) AS sla_breach_pct
FROM fact_complaints
GROUP BY is_incident_day;
