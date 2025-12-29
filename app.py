import streamlit as st
import snowflake.connector
from datetime import date

st.title("Central Bank Interest Rates")

st.markdown("""
This app allows you to update Central Bank interest rates securely to Snowflake.
""")

# 1. Choose Central Bank
central_bank = st.selectbox(
    "Choose Central Bank",
    ("ECB", "BoE")
)

# 2. Interest Rate
# "values are only like 2.15%, so percentable values"
interest_rate = st.number_input(
    "Interest Rate (%)",
    min_value=-10.0, # Interest rates can be negative
    max_value=100.0,
    value=2.15,
    step=0.01,
    format="%.2f"
)

# 3. Last Change Date
change_date = st.date_input(
    "Last Change Date",
    value=date.today()
)

if st.button("Submit"):
    # Secure connection to Snowflake
    try:
        # Check if secrets are available
        # Streamlit secrets are accessed via st.secrets
        # We expect a section named [snowflake]
        if 'snowflake' not in st.secrets:
            st.error("Snowflake secrets are not configured. Please set them in `.streamlit/secrets.toml` or as environment variables on your deployment platform.")
            st.code("""
# Example .streamlit/secrets.toml
[snowflake]
user = "your_username"
password = "your_password"
account = "your_account_identifier"
warehouse = "your_warehouse"
database = "INTEREST_RATES"
schema = "PUBLIC"
            """, language="toml")
            st.stop()

        # Establish connection
        # It is recommended to use st.connection("snowflake") if available in newer streamlit versions or manual connection like this
        conn = snowflake.connector.connect(
            user=st.secrets["snowflake"]["user"],
            password=st.secrets["snowflake"]["password"],
            account=st.secrets["snowflake"]["account"],
            warehouse=st.secrets["snowflake"].get("warehouse"),
            database=st.secrets["snowflake"].get("database", "INTEREST_RATES"),
            schema=st.secrets["snowflake"].get("schema", "PUBLIC")
        )

        cursor = conn.cursor()

        # Use parameterized query to prevent SQL injection
        # Assuming the table structure matches the inputs
        query = """
        INSERT INTO INTEREST_RATES.PUBLIC.CENTRAL_BANK_RATES
        (CENTRAL_BANK, INTEREST_RATE, LAST_CHANGE_DATE)
        VALUES (%s, %s, %s)
        """

        cursor.execute(query, (central_bank, interest_rate, change_date))

        conn.commit()
        st.success(f"Successfully added record for {central_bank} with rate {interest_rate}% on {change_date}.")

    except snowflake.connector.errors.ProgrammingError as e:
        st.error(f"Snowflake Programming Error: {e}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
