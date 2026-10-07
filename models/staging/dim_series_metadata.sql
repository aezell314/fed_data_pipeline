with src_series_metadata as (
    select * from {{ ref('src_series_metadata') }}
)
SELECT
    series_id,
    title,
    observation_start::date as observation_start,
    observation_end::date as observation_end,
    frequency,
    units,
    seasonal_adjustment,
    last_updated::timestamp as last_updated,
    popularity::integer as popularity,
    upper(state) as state_code
FROM
    src_series_metadata