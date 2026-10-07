--implementing a snapshot for unemployment data since historical values can change if new data is found
snapshots:
  - name: scd_raw_unemployment
    relation: source('fed_data_pipeline', 'unemployment')
    config:
      unique_key: id
      strategy: timestamp
      updated_at: realtime_end
      hard_deletes: invalidate