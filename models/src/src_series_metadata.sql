with raw_series_metadata as (
    select * from {{ source('fed_data_pipeline','series_metadata') }}
)
SELECT
    *
FROM
    raw_series_metadata