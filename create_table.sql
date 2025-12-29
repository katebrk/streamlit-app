create or replace table central_bank_rates (
    central_bank_full_name VARCHAR(100),
    central_bank_short_name VARCHAR(100),
    rate_pct NUMBER(5,2),
    last_change_date DATE, 
    created_on DATETIME
    --,type VARCHAR(100),
    --forecast_date DATE
);
