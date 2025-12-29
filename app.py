import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from datetime import date, datetime

st.title("Central Bank Interest Rates (SiS)")

st.markdown("""
This app updates Central Bank interest rates directly within Snowflake.
""")

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
    try:
        # Get the active session in Streamlit in Snowflake
        session = get_active_session()

        # Construct the SQL statement
        # Table: central_bank_rates
        # Columns: central_bank_full_name, central_bank_short_name, rate_pct, last_change_date, created_on
        # central_bank_full_name should be NULL

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
        # "append" mode adds the data.
        snowpark_df.write.mode("append").save_as_table("central_bank_rates")

        st.success(f"Successfully added record for {central_bank_short} with rate {rate_pct}% on {last_change_date}.")

        # Show table with the latest submitted values (last 20)
        st.subheader("Latest Submissions")
        latest_df = session.sql("""
            SELECT *
            FROM central_bank_rates
            ORDER BY created_on DESC
            LIMIT 20
        """).to_pandas()

        st.dataframe(latest_df)

    except Exception as e:
        st.error(f"An error occurred: {e}")
