# Streamlit in Snowflake (SiS) App

This repository contains the code for a Streamlit application designed to run **directly inside Snowflake** (Streamlit in Snowflake).

## Purpose

The app allows users to manually input interest rate data for central banks (ECB, BoE) and insert it into a Snowflake table. It supports specifying whether the rate is "Actual" or "Forecast" and provides a forecast date where applicable.

## Snowflake Table Schema

The app expects the following table to exist in your Snowflake environment:

```sql
create table central_bank_rates (
    central_bank_full_name VARCHAR(100),
    central_bank_short_name VARCHAR(100),
    rate_pct NUMBER(5,2),
    last_change_date DATE,
    type VARCHAR(20),
    forecast_date DATE,
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

## Features

*   **Input Form**: Submit new interest rate entries.
    *   Dynamic "Forecast Date" field (disabled when "Type" is "Actual").
*   **Latest Submissions Table**:
    *   View the last 20 submissions.
    *   **Edit**: Modify existing values. If "Type" is changed to "Actual", "Forecast Date" is automatically cleared.
    *   **Add**: Add new rows directly in the table.
    *   **Delete**: Remove rows.

## Dependencies

When configuring the app in Snowflake, ensure the following packages are selected:
*   `snowflake-snowpark-python`
*   `pandas`
*   `streamlit`
