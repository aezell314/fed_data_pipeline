with raw_state_product as (
    select * from {{ source('fed_data_pipeline','state_product') }}
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
    raw_state_product