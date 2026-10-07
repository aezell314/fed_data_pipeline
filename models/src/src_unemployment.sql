with raw_unemployment as (
    select * from {{ source('fed_data_pipeline','unemployment') }}
)
SELECT
    {{ dbt_utils.generate_surrogate_key(['date', 'state']) }}
    AS id,
    realtime_start,
    realtime_end,
    date,
    NULLIF(value, '.') as value,
    state,
    series_id
FROM
    raw_unemployment