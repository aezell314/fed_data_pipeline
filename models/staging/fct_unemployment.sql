WITH src_unemployment as (
    SELECT * FROM {{ ref('src_unemployment') }}
)
SELECT
    EXTRACT(YEAR FROM date::date) as economic_year,
    upper(state) as state_code,
    series_id,
     --aggregate by year to match grain of CPI and GSP data
    avg(cast(value as decimal(10,2))) as unemployment_rate 
FROM    
    src_unemployment
GROUP BY ALL