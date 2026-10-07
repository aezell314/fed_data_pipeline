WITH src_state_product as (
    SELECT * FROM {{ ref('src_state_product') }}
)
SELECT
    EXTRACT(YEAR FROM date::date) as economic_year,
    upper(state) as state_code,
    series_id,
    cast(value as decimal(10,2)) as gsp_value
FROM    
    src_state_product