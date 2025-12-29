import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from datetime import date, datetime

st.title("Central Bank Interest Rates (SiS)")

st.markdown("""
This app updates Central Bank interest rates directly within Snowflake.
""")

# Get the active session in Streamlit in Snowflake
# We get it outside the button to use it for fetching data
try:
    session = get_active_session()
except:
    session = None

# 1. Choose Central Bank
# Options: ECB, BoE
central_bank_short = st.selectbox(
    "Choose Central Bank",
    ("ECB", "BoE")
)

# 2. Interest Rate
# "values are only like 2.15%, so percentable values"
rate_pct = st.number_input(
    "Interest Rate (%)",
    min_value=-10.0,
    max_value=100.0,
    value=2.15,
    step=0.01,
    format="%.2f"
)

# 3. Type (Actual / Forecast)
rate_type = st.selectbox(
    "Type",
    ("Actual", "Forecast")
)

# 4. Forecast Date (Conditional)
# 5. Last Change Date
col1, col2 = st.columns(2)

with col1:
    last_change_date = st.date_input(
        "Last Change Date",
        value=date.today()
    )

with col2:
    # Show disabled input if Actual to make it clear the field exists
    is_forecast = (rate_type == "Forecast")

    forecast_date_input = st.date_input(
        "Forecast Date",
        value=date.today(),
        disabled=not is_forecast
    )

    if is_forecast:
        forecast_date = forecast_date_input
    else:
        forecast_date = None

if st.button("Submit"):
    if session:
        try:
            # Explicit SQL Insert to avoid column order mismatch issues
            insert_sql = """
            INSERT INTO central_bank_rates
            (CENTRAL_BANK_FULL_NAME, CENTRAL_BANK_SHORT_NAME, RATE_PCT, LAST_CHANGE_DATE, TYPE, FORECAST_DATE, CREATED_ON)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            # Params must match the order in the VALUES clause
            params = [
                None,
                central_bank_short,
                rate_pct,
                last_change_date,
                rate_type,
                forecast_date,
                datetime.now() # Use standard python datetime
            ]

            session.sql(insert_sql, params=params).collect()

            st.success(f"Successfully added record for {central_bank_short} ({rate_type}).")

        except Exception as e:
            st.error(f"An error occurred during submission: {e}")
    else:
        st.error("Could not get active Snowflake session.")


# --- Display and Edit Latest Submissions ---
st.divider()
st.subheader("Latest Submissions")

if session:
    try:
        # Fetch only the requested columns
        query = """
            SELECT
                CENTRAL_BANK_SHORT_NAME,
                RATE_PCT,
                LAST_CHANGE_DATE,
                TYPE,
                FORECAST_DATE,
                CREATED_ON
            FROM central_bank_rates
            ORDER BY CREATED_ON DESC
            LIMIT 20
        """
        # Load into Pandas for the editor
        latest_df = session.sql(query).to_pandas()

        # Display Data Editor
        # Key is important to track state
        edited_df = st.data_editor(
            latest_df,
            key="latest_submissions_editor",
            column_config={
                "CENTRAL_BANK_SHORT_NAME": st.column_config.SelectboxColumn(
                    "Central Bank",
                    options=["ECB", "BoE"],
                    required=True
                ),
                "RATE_PCT": st.column_config.NumberColumn(
                    "Rate (%)",
                    min_value=-10.0,
                    max_value=100.0,
                    step=0.01,
                    format="%.2f",
                    required=True
                ),
                "LAST_CHANGE_DATE": st.column_config.DateColumn(
                    "Last Change Date",
                    required=True
                ),
                "TYPE": st.column_config.SelectboxColumn(
                    "Type",
                    options=["Actual", "Forecast"],
                    required=True
                ),
                "FORECAST_DATE": st.column_config.DateColumn(
                    "Forecast Date",
                    required=False
                ),
                "CREATED_ON": st.column_config.DatetimeColumn(
                    "Created On",
                    disabled=True
                )
            },
            num_rows="dynamic", # Allow adding/deleting rows
            use_container_width=True
        )

        if st.button("Save Changes to Table"):
            editor_state = st.session_state.get("latest_submissions_editor")

            updates_count = 0
            deletes_count = 0
            added_count = 0

            if editor_state:
                # 1. Handle Added Rows
                if editor_state.get("added_rows"):
                    added_rows = editor_state["added_rows"]

                    insert_sql = """
                    INSERT INTO central_bank_rates
                    (CENTRAL_BANK_FULL_NAME, CENTRAL_BANK_SHORT_NAME, RATE_PCT, LAST_CHANGE_DATE, TYPE, FORECAST_DATE, CREATED_ON)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """

                    for row in added_rows:
                        # Ensure required fields are present (checking keys)
                        if "CENTRAL_BANK_SHORT_NAME" in row and "RATE_PCT" in row and "LAST_CHANGE_DATE" in row and "TYPE" in row:

                            r_type = row["TYPE"]
                            r_forecast_date = row.get("FORECAST_DATE")

                            # Enforce constraint: If Type is Actual, Forecast Date is NULL
                            if r_type == "Actual":
                                r_forecast_date = None

                            # Convert dates safely to python date objects
                            # pd.to_datetime returns Timestamp, .date() converts to datetime.date
                            p_last_change = pd.to_datetime(row["LAST_CHANGE_DATE"]).date()

                            if r_forecast_date:
                                p_forecast = pd.to_datetime(r_forecast_date).date()
                            else:
                                p_forecast = None

                            params = [
                                None,
                                row["CENTRAL_BANK_SHORT_NAME"],
                                row["RATE_PCT"],
                                p_last_change,
                                r_type,
                                p_forecast,
                                datetime.now()
                            ]

                            session.sql(insert_sql, params=params).collect()
                            added_count += 1

                # 2. Handle Deleted Rows
                if editor_state.get("deleted_rows"):
                    deleted_rows = editor_state["deleted_rows"]
                    for idx in deleted_rows:
                        row_key = latest_df.iloc[idx]["CREATED_ON"]
                        # row_key is Timestamp, convert to string or datetime for safety if needed,
                        # but usually param binding handles existing timestamps fine.
                        # Using str(row_key) is often safe for simple equality checks.
                        sql_delete = "DELETE FROM central_bank_rates WHERE CREATED_ON = ?"
                        session.sql(sql_delete, params=[str(row_key)]).collect()
                        deletes_count += 1

                # 3. Handle Edited Rows
                if editor_state.get("edited_rows"):
                    edited_rows = editor_state["edited_rows"]

                    for idx, changes in edited_rows.items():
                        # idx is the integer index in the dataframe
                        original_row = latest_df.iloc[idx]
                        row_key = original_row["CREATED_ON"]

                        # Determine final values to check constraint
                        # We need to know if TYPE is effectively 'Actual'

                        # Current values (from original)
                        current_type = original_row["TYPE"]
                        current_forecast = original_row["FORECAST_DATE"]

                        # New values (from changes)
                        new_type = changes.get("TYPE", current_type)
                        new_forecast = changes.get("FORECAST_DATE", current_forecast)

                        # Enforce Constraint
                        if new_type == "Actual":
                            # If effective type is Actual, force forecast date to None
                            # We must ensure this is reflected in the update
                            # If forecast date was not None, or if user tried to set it
                            if new_forecast is not None:
                                changes["FORECAST_DATE"] = None

                        # Construct UPDATE parts
                        set_clauses = []
                        params = []

                        for col_name, new_value in changes.items():
                            set_clauses.append(f"{col_name} = ?")

                            # Handle potential conversions if new_value is ambiguous
                            # st.data_editor might return strings for dates
                            # But usually parameterized queries handle strings for dates OK.
                            # If we want to be super strict, we could check types.
                            # For now, we trust basic binding unless it fails.
                            params.append(new_value)

                        if set_clauses:
                            params.append(str(row_key))

                            sql_update = f"""
                            UPDATE central_bank_rates
                            SET {", ".join(set_clauses)}
                            WHERE CREATED_ON = ?
                            """

                            session.sql(sql_update, params=params).collect()
                            updates_count += 1

                if added_count > 0 or updates_count > 0 or deletes_count > 0:
                    st.success(f"Saved changes: {added_count} added, {updates_count} updated, {deletes_count} deleted.")
                    st.rerun()
                else:
                    st.info("No changes to save.")
            else:
                st.info("No changes detected.")

    except Exception as e:
        st.error(f"An error occurred fetching or updating data: {e}")
else:
    st.info("No active Snowflake session detected (Local mode).")
