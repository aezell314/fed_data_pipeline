with raw_price_index as (
    select * from {{ source('fed_data_pipeline','personal_income') }}
)
SELECT
    {{ dbt_utils.generate_surrogate_key(['date', 'state']) }}
    AS id,
    realtime_start,
    realtime_end,
    date,
    value,
    state,
    series_id
FROM
    raw_price_index