snapshots:
  - name: scd_raw_series_metadata
    relation: source('fed_data_pipeline', 'series_metadata')
    config:
      unique_key: series_id
      strategy: timestamp
      updated_at: last_updated
      hard_deletes: invalidate