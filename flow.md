                ┌───────────────────┐
                │   S3 Inventory    │
                │(Daily/Weekly Gen.)│
                └───────┬──────────┘
                        │ Inventory Complete
                        v
              ┌────────────────────────────────┐
              │ S3 Inventory Bucket             │
              │ (Manifest & CSV Files)          │
              └───────┬────────────────────────┘
                      │ S3 PutObject Event/Trigger
                      v
               ┌───────────────────────┐
               │   Lambda Preprocessor  │
               │   (Filtering Logic)    │
               └───────┬───────────────┘
                       │
                       │ 1. Read prefix config
                       v
             ┌───────────────────────┐
             │   DynamoDB Table       │
             │  (Prefix Config)       │
             └───┬────────────────────┘
                 │ 2. Return prefix list
                 v
       ┌─────────────────────────────────┐
       │   Lambda Continues:             │
       │  - Download manifest & CSVs      │
       │  - Filter by prefixes            │
       │  - Generate filtered manifest    │
       └─────────────────┬───────────────┘
                          │ 3. Upload filtered manifest & CSV
                          v
                 ┌───────────────────────┐
                 │ S3 Inventory Bucket    │
                 │(Filtered Manifest)     │
                 └─────────┬─────────────┘
                           │ 4. Notify or Trigger Next Step
                           v
               ┌─────────────────────────────────┐
               │ S3 Batch Operations Job Creation │
               │   (Uses Filtered Manifest)       │
               └───────┬─────────────────────────┘
                       │ 5. Execute Batch Job
                       v
               ┌────────────────────────────────┐
               │  S3 Batch Operations            │
               │  - Processes filtered objects   │
               │    (e.g., COPY to archive)      │
               └────────────────────────────────┘
