# Central Bank Interest Rates App

This is a Streamlit app that allows users to input interest rates for central banks (ECB, BoE) and store them in a Snowflake table.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Secrets:**
    Create a `.streamlit/secrets.toml` file in the root directory (or configure secrets in your Streamlit Cloud dashboard).

    ```toml
    [snowflake]
    user = "your_username"
    password = "your_password"
    account = "your_account_identifier"
    warehouse = "your_warehouse"
    database = "INTEREST_RATES"
    schema = "PUBLIC"
    ```

    *Note: Do not commit `.streamlit/secrets.toml` to version control.*

3.  **Run the App:**
    ```bash
    streamlit run app.py
    ```

## Functionality

*   **Choose Central Bank:** Select between ECB and BoE.
*   **Interest Rate:** Input the interest rate percentage.
*   **Last Change Date:** Select the date of the last rate change.
*   **Submit:** Inserts the data into `INTEREST_RATES.PUBLIC.CENTRAL_BANK_RATES`.

## Security

This app uses Streamlit Secrets management to handle Snowflake credentials securely. No credentials are hardcoded in the source code.
