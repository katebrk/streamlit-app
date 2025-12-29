import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from datetime import date

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

# 3. Last Change Date
last_change_date = st.date_input(
    "Last Change Date",
    value=date.today()
)

if st.button("Submit"):
    if session:
        try:
            # Prepare data for insertion
            df_data = pd.DataFrame([{
                "CENTRAL_BANK_FULL_NAME": None,
                "CENTRAL_BANK_SHORT_NAME": central_bank_short,
                "RATE_PCT": rate_pct,
                "LAST_CHANGE_DATE": pd.to_datetime(last_change_date),
                "CREATED_ON": pd.Timestamp.now()
            }])

            # Create a Snowpark DataFrame
            snowpark_df = session.create_dataframe(df_data)

            # Write to the table
            snowpark_df.write.mode("append").save_as_table("central_bank_rates")

            st.success(f"Successfully added record for {central_bank_short} with rate {rate_pct}% on {last_change_date}.")

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
                    "Date",
                    required=True
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
                    new_records = []

                    for row in added_rows:
                        # Ensure required fields are present (checking keys)
                        # Note: In the editor, 'CREATED_ON' will be missing or ignored
                        if "CENTRAL_BANK_SHORT_NAME" in row and "RATE_PCT" in row and "LAST_CHANGE_DATE" in row:
                            new_records.append({
                                "CENTRAL_BANK_FULL_NAME": None,
                                "CENTRAL_BANK_SHORT_NAME": row["CENTRAL_BANK_SHORT_NAME"],
                                "RATE_PCT": row["RATE_PCT"],
                                "LAST_CHANGE_DATE": pd.to_datetime(row["LAST_CHANGE_DATE"]),
                                "CREATED_ON": pd.Timestamp.now()
                            })

                    if new_records:
                        df_new = pd.DataFrame(new_records)
                        # Append to Snowflake table
                        session.create_dataframe(df_new).write.mode("append").save_as_table("central_bank_rates")
                        added_count = len(new_records)

                # 2. Handle Deleted Rows
                if editor_state.get("deleted_rows"):
                    deleted_rows = editor_state["deleted_rows"]
                    for idx in deleted_rows:
                        # idx is the integer index in the ORIGINAL dataframe
                        row_key = latest_df.iloc[idx]["CREATED_ON"]

                        sql_delete = "DELETE FROM central_bank_rates WHERE CREATED_ON = ?"
                        session.sql(sql_delete, params=[str(row_key)]).collect()
                        deletes_count += 1

                # 3. Handle Edited Rows
                if editor_state.get("edited_rows"):
                    edited_rows = editor_state["edited_rows"]

                    for idx, changes in edited_rows.items():
                        # idx is the integer index in the dataframe
                        # Get the unique identifier (CREATED_ON) from the ORIGINAL dataframe (latest_df)
                        row_key = latest_df.iloc[idx]["CREATED_ON"]

                        # Construct UPDATE parts
                        set_clauses = []
                        params = []

                        # 'changes' is a dict of {ColName: NewValue}
                        for col_name, new_value in changes.items():
                            set_clauses.append(f"{col_name} = ?")
                            params.append(new_value)

                        if set_clauses:
                            # Add key to params
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
                    # Rerun to refresh the table
                    st.rerun()
                else:
                    st.info("No changes to save.")
            else:
                st.info("No changes detected.")

    except Exception as e:
        st.error(f"An error occurred fetching or updating data: {e}")
else:
    st.info("No active Snowflake session detected (Local mode).")
