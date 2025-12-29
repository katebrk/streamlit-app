# Streamlit in Snowflake (SiS) App

This repository contains the code for a Streamlit application designed to run **directly inside Snowflake** (Streamlit in Snowflake).

## Purpose

The app allows users to manually input interest rate data for central banks (ECB, BoE) and insert it into a Snowflake table. It also records the timestamp of the submission and displays the last 20 submissions.

## Snowflake Table Schema

The app expects the following table to exist in your Snowflake environment:

```sql
create table central_bank_rates (
    central_bank_full_name VARCHAR(100),
    central_bank_short_name VARCHAR(100),
    rate_pct NUMBER(5,2),
    last_change_date DATE,
    created_on TIMESTAMP
);
```

## How to Deploy

1.  Log in to Snowsight (Snowflake Web Interface).
2.  Navigate to **Streamlit** in the left menu.
3.  Click **+ Streamlit App**.
4.  Provide a name and select the Warehouse and Database/Schema where the `central_bank_rates` table resides.
5.  Paste the contents of `app.py` into the editor.
6.  Click **Run**.

## Local Development

*Note: This code is specifically written for the Streamlit in Snowflake environment and uses `snowflake.snowpark.context.get_active_session()`. It will not run locally without modification or a mock session.*

## Dependencies

When configuring the app in Snowflake, ensure the following packages are selected (usually available by default or via Anaconda integration):
*   `snowflake-snowpark-python`
*   `pandas`
*   `streamlit`
