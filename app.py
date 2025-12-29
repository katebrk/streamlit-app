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
            disabled=["CREATED_ON"], # Prevent editing the key
            num_rows="fixed", # Don't allow adding/deleting rows, only editing
            use_container_width=True
        )

        # Check if changes were made
        # st.data_editor returns the dataframe with changes applied.
        # However, to perform the DB update, we need to know what changed or just iterate.
        # Since we only have 20 rows, we can check for differences or use the session state 'edited_rows'

        if st.button("Save Changes to Table"):
            # Check the editor state to see what rows were modified
            # st.session_state["latest_submissions_editor"] contains:
            # {
            #   "edited_rows": {0: {"RATE_PCT": 2.5}, ...},
            #   "added_rows": [],
            #   "deleted_rows": []
            # }

            editor_state = st.session_state.get("latest_submissions_editor")

            if editor_state and editor_state.get("edited_rows"):
                edited_rows = editor_state["edited_rows"]

                updates_count = 0

                for idx, changes in edited_rows.items():
                    # idx is the integer index in the dataframe
                    # Get the unique identifier (CREATED_ON) from the ORIGINAL dataframe (latest_df)
                    # We must use the original 'latest_df' because the index corresponds to it.
                    row_key = latest_df.iloc[idx]["CREATED_ON"]

                    # Construct UPDATE parts
                    set_clauses = []
                    params = []

                    # 'changes' is a dict of {ColName: NewValue}
                    for col_name, new_value in changes.items():
                        # Handle type conversions if necessary, though Snowpark SQL usually handles basic types
                        # Note: Date objects might need formatting
                        set_clauses.append(f"{col_name} = ?")
                        params.append(new_value)

                    if set_clauses:
                        # Add key to params
                        params.append(str(row_key)) # Cast to string/timestamp format if needed, but parameter binding handles it usually

                        sql_update = f"""
                        UPDATE central_bank_rates
                        SET {", ".join(set_clauses)}
                        WHERE CREATED_ON = ?
                        """

                        # Execute Update
                        # session.sql(sql, params=params).collect()
                        # Note: Snowpark session.sql() param binding behavior:
                        session.sql(sql_update, params=params).collect()
                        updates_count += 1

                if updates_count > 0:
                    st.success(f"Updated {updates_count} row(s).")
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
