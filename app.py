import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from datetime import date, datetime

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def get_session():
    """Safely get the active Snowflake session."""
    try:
        return get_active_session()
    except Exception:
        return None

def safe_to_date(val):
    """
    Convert a value to a python datetime.date object or None.
    Streamlit date inputs return datetime.date.
    Pandas conversions might return Timestamp.
    """
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        # Attempt to parse strings or pandas Timestamps
        dt = pd.to_datetime(val)
        if pd.isnull(dt):
            return None
        return dt.date()
    except:
        return None

# -----------------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------------

st.title("Central Bank Interest Rates (SiS)")
st.markdown("Update Central Bank interest rates directly within Snowflake.")

session = get_session()

if not session:
    st.warning("No active Snowflake session detected. App is in read-only/local mode.")

# -----------------------------------------------------------------------------
# 1. Submission Form
# -----------------------------------------------------------------------------
st.header("New Submission")

with st.form("submission_form"):
    col_bank, col_rate, col_type = st.columns(3)

    with col_bank:
        central_bank_short = st.selectbox("Central Bank", ("ECB", "BoE"))

    with col_rate:
        rate_pct = st.number_input(
            "Interest Rate (%)",
            min_value=-10.0, max_value=100.0, value=2.15, step=0.01, format="%.2f"
        )

    with col_type:
        rate_type = st.selectbox("Type", ("Actual", "Forecast"))

    col_date, col_forecast = st.columns(2)

    with col_date:
        last_change_date = st.date_input("Last Change Date", value=date.today())

    with col_forecast:
        # Conditional Logic: If Actual, disabled.
        is_forecast = (rate_type == "Forecast")
        forecast_date_input = st.date_input(
            "Forecast Date",
            value=date.today(),
            disabled=not is_forecast
        )

    submit_btn = st.form_submit_button("Submit Record")

    if submit_btn:
        if session:
            try:
                # Business Logic: Force NULL if Actual
                final_forecast_date = forecast_date_input if is_forecast else None

                # Insert SQL
                # Note: We pass NULL for central_bank_full_name explicitly in SQL
                insert_query = """
                INSERT INTO central_bank_rates
                (CENTRAL_BANK_FULL_NAME, CENTRAL_BANK_SHORT_NAME, RATE_PCT, LAST_CHANGE_DATE, TYPE, FORECAST_DATE, CREATED_ON)
                VALUES (NULL, ?, ?, ?, ?, ?, ?)
                """

                # Parameters - strictly typed
                # CREATED_ON is a timestamp
                created_on_ts = datetime.now()

                params = [
                    central_bank_short,
                    rate_pct,
                    safe_to_date(last_change_date),
                    rate_type,
                    safe_to_date(final_forecast_date),
                    created_on_ts
                ]

                session.sql(insert_query, params=params).collect()
                st.success(f"Added: {central_bank_short} - {rate_pct}% ({rate_type})")

            except Exception as e:
                st.error(f"Error submitting data: {e}")
        else:
            st.error("Session required to submit.")

# -----------------------------------------------------------------------------
# 2. Latest Submissions (Add/Edit/Delete)
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Latest Submissions (Last 20)")

if session:
    try:
        # Fetch Data
        df_latest = session.sql("""
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
        """).to_pandas()

        # Configure Editor
        edited_df = st.data_editor(
            df_latest,
            key="submissions_editor",
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "CENTRAL_BANK_SHORT_NAME": st.column_config.SelectboxColumn("Bank", options=["ECB", "BoE"], required=True),
                "RATE_PCT": st.column_config.NumberColumn("Rate (%)", format="%.2f", required=True),
                "LAST_CHANGE_DATE": st.column_config.DateColumn("Change Date", required=True),
                "TYPE": st.column_config.SelectboxColumn("Type", options=["Actual", "Forecast"], required=True),
                "FORECAST_DATE": st.column_config.DateColumn("Forecast Date"),
                "CREATED_ON": st.column_config.DatetimeColumn("Created On", disabled=True),
            }
        )

        # Save Button
        if st.button("Save Changes"):
            changes = st.session_state["submissions_editor"]

            added_rows = changes.get("added_rows", [])
            deleted_rows = changes.get("deleted_rows", [])
            edited_rows = changes.get("edited_rows", {})

            # Counters
            cnt_add = 0
            cnt_del = 0
            cnt_upd = 0

            # A. Handle Additions
            if added_rows:
                insert_sql_add = """
                INSERT INTO central_bank_rates
                (CENTRAL_BANK_FULL_NAME, CENTRAL_BANK_SHORT_NAME, RATE_PCT, LAST_CHANGE_DATE, TYPE, FORECAST_DATE, CREATED_ON)
                VALUES (NULL, ?, ?, ?, ?, ?, ?)
                """
                for row in added_rows:
                    # Validate required fields exist in the dict
                    if all(k in row for k in ["CENTRAL_BANK_SHORT_NAME", "RATE_PCT", "LAST_CHANGE_DATE", "TYPE"]):

                        r_type = row["TYPE"]
                        r_forecast = row.get("FORECAST_DATE") # Might be None/Missing

                        # Rule: If Actual -> Forecast is None
                        if r_type == "Actual":
                            r_forecast = None

                        # Typed Params
                        params_add = [
                            row["CENTRAL_BANK_SHORT_NAME"],
                            row["RATE_PCT"],
                            safe_to_date(row["LAST_CHANGE_DATE"]),
                            r_type,
                            safe_to_date(r_forecast),
                            datetime.now()
                        ]

                        session.sql(insert_sql_add, params=params_add).collect()
                        cnt_add += 1

            # B. Handle Deletions
            if deleted_rows:
                del_sql = "DELETE FROM central_bank_rates WHERE CREATED_ON = ?"
                for idx in deleted_rows:
                    # Use original dataframe to get the key
                    key = df_latest.iloc[idx]["CREATED_ON"]
                    # Pass timestamp/string as param
                    session.sql(del_sql, params=[str(key)]).collect()
                    cnt_del += 1

            # C. Handle Edits
            if edited_rows:
                for idx, row_changes in edited_rows.items():
                    # Reference original row
                    orig_row = df_latest.iloc[idx]
                    key = orig_row["CREATED_ON"]

                    # Logic to determine final values to enforce constraints
                    curr_type = orig_row["TYPE"]
                    curr_forecast = orig_row["FORECAST_DATE"]

                    new_type = row_changes.get("TYPE", curr_type)
                    new_forecast = row_changes.get("FORECAST_DATE", curr_forecast)

                    # Check Constraint
                    # If the effective type is Actual, we MUST force Forecast to NULL
                    # We inject this into row_changes if it's not consistent
                    if new_type == "Actual":
                         if new_forecast is not None:
                             row_changes["FORECAST_DATE"] = None

                    # Build Dynamic UPDATE
                    set_parts = []
                    upd_params = []

                    for col, val in row_changes.items():
                        set_parts.append(f"{col} = ?")

                        # Special handling for dates vs others
                        if col in ["LAST_CHANGE_DATE", "FORECAST_DATE"]:
                            upd_params.append(safe_to_date(val))
                        else:
                            upd_params.append(val)

                    if set_parts:
                        # Append Key
                        upd_params.append(str(key))

                        upd_sql = f"""
                        UPDATE central_bank_rates
                        SET {', '.join(set_parts)}
                        WHERE CREATED_ON = ?
                        """
                        session.sql(upd_sql, params=upd_params).collect()
                        cnt_upd += 1

            # Refresh if changes made
            if cnt_add + cnt_del + cnt_upd > 0:
                st.success(f"Changes Saved: {cnt_add} Added, {cnt_upd} Updated, {cnt_del} Deleted.")
                st.rerun()
            else:
                st.info("No valid changes detected.")

    except Exception as e:
        st.error(f"Error fetching or saving table data: {e}")
