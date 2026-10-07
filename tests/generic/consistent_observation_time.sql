{% test consistent_observation_time(model) %}
{# checks that the year values for each economic data series fall within the range observation_start - observation_end 
listed in the series_metadata table #}
select *
from {{ model }} m
inner join {{ ref('dim_series_metadata') }} d
on m.series_id = d.series_id
and (m.economic_year < (extract(year from d.observation_start))
or m.economic_year > (extract(year from d.observation_end)))
LIMIT 10
{% endtest %}