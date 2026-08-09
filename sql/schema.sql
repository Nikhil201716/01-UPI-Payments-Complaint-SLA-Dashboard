-- schema.sql
-- Normalized SQLite schema for the UPI Payments Complaint & SLA Analytics
-- Dashboard project. A star-schema style design: one fact table
-- (fact_complaints) surrounded by small dimension tables, instead of one
-- giant flat spreadsheet. This mirrors how real companies structure data
-- warehouses so that BI tools and analysts can query it efficiently.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_complaints;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_channel;
DROP TABLE IF EXISTS dim_agent;

CREATE TABLE dim_category (
    category_id       INTEGER PRIMARY KEY,
    category_name     TEXT NOT NULL,
    category_group    TEXT NOT NULL,
    sla_target_hours  INTEGER NOT NULL
);

CREATE TABLE dim_channel (
    channel_id    INTEGER PRIMARY KEY,
    channel_name  TEXT NOT NULL
);

CREATE TABLE dim_agent (
    agent_id    INTEGER PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    team        TEXT NOT NULL
);

CREATE TABLE fact_complaints (
    ticket_id            INTEGER PRIMARY KEY,
    customer_id          TEXT NOT NULL,
    category_id          INTEGER NOT NULL,
    channel_id           INTEGER NOT NULL,
    agent_id             INTEGER,                 -- nullable: some raw tickets arrive unassigned
    transaction_amount_inr REAL,
    opened_at            TEXT NOT NULL,            -- ISO 8601 'YYYY-MM-DD HH:MM:SS'
    closed_at            TEXT,                     -- ISO 8601 or NULL if still open
    status                TEXT NOT NULL CHECK (status IN ('Open','Closed')),
    resolution_hours     REAL,
    sla_target_hours     INTEGER NOT NULL,
    sla_breached         INTEGER NOT NULL CHECK (sla_breached IN (0,1)),
    root_cause           TEXT,
    is_incident_day      INTEGER NOT NULL CHECK (is_incident_day IN (0,1)),
    FOREIGN KEY (category_id) REFERENCES dim_category(category_id),
    FOREIGN KEY (channel_id)  REFERENCES dim_channel(channel_id),
    FOREIGN KEY (agent_id)    REFERENCES dim_agent(agent_id)
);

CREATE INDEX idx_complaints_opened_at   ON fact_complaints(opened_at);
CREATE INDEX idx_complaints_category    ON fact_complaints(category_id);
CREATE INDEX idx_complaints_channel     ON fact_complaints(channel_id);
CREATE INDEX idx_complaints_sla_breach  ON fact_complaints(sla_breached);
CREATE INDEX idx_complaints_status      ON fact_complaints(status);
