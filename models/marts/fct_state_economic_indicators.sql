with pcpi as (
    select economic_year, state_code, pcpi_value, series_id from {{ ref('fct_personal_income') }}
),
gsp as (
    select economic_year, state_code, gsp_value, series_id from {{ ref('fct_state_product') }}
),
unemployment as (
    select economic_year, state_code, unemployment_rate, series_id from {{ ref('fct_unemployment') }}
),
series_metadata as (
    select title, units, seasonal_adjustment, series_id from {{ ref('dim_series_metadata') }}
)
select
    coalesce(pcpi.economic_year, gsp.economic_year, unemployment.economic_year) as economic_year,
    coalesce(pcpi.state_code, gsp.state_code, unemployment.state_code) as state_code,
    pcpi.pcpi_value,
    gsp.gsp_value,
    unemployment.unemployment_rate,
    series_metadata.title,
    series_metadata.units,
    series_metadata.seasonal_adjustment
from pcpi
full outer join gsp 
    on pcpi.economic_year = gsp.economic_year and pcpi.state_code = gsp.state_code
full outer join unemployment 
    on pcpi.economic_year = unemployment.economic_year and pcpi.state_code = unemployment.state_code
left join series_metadata
    on pcpi.series_id = series_metadata.series_id

