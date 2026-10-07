{% macro maintain_ducklake() %}
  {{ log("Running DuckLake Snapshot Cleanup & Vacuum...", info=True) }}
  
  -- Use explicit named argument assignments (:=) to match the signature
  {% set sync_query %}
    SELECT * FROM ducklake_cleanup_old_files(
        'lake', 
        cleanup_all := TRUE, 
        dry_run := FALSE
    );
  {% endset %}

  {% set expire_query %}
    SELECT * FROM ducklake_expire_snapshots(
        'lake', 
        older_than := now() - INTERVAL '0 seconds'
        );
  {% endset %}
  
  {% do run_query(sync_query) %}

  {% do run_query(expire_query) %}

  {{ log("DuckLake optimization complete.", info=True) }}
{% endmacro %}
