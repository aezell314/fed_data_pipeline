WITH src_price_index as (
    SELECT * FROM {{ ref('src_personal_income') }}
)
SELECT
    EXTRACT(YEAR FROM date::date) as economic_year,
    upper(state) as state_code,
    series_id,
    cast(value as decimal(10,2)) as pcpi_value
FROM    
    src_price_index