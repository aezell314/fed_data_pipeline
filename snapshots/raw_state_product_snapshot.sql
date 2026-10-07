--implementing a snapshot for GSP data since historical values can change if new data is found
snapshots:
  - name: scd_raw_state_product
    relation: source('fed_data_pipeline', 'state_product')
    config:
      unique_key: id
      strategy: timestamp
      updated_at: realtime_end
      hard_deletes: invalidate