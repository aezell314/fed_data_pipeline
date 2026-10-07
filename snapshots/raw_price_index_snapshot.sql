--implementing a snapshot for CPI data since historical values can change if new data is found
snapshots:
  - name: scd_raw_price_index
    relation: source('fed_data_pipeline', 'price_index')
    config:
      unique_key: id
      strategy: timestamp
      updated_at: realtime_end
      hard_deletes: invalidate