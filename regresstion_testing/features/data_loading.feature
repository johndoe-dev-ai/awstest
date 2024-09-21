Feature: Data Loading

  Scenario: Load Parquet files into Redshift successfully
    Given a valid Parquet file in S3 at "s3://your-bucket/output/valid_data.parquet"
    When the data loading process is executed
    Then the data is accurately loaded into the Redshift table "public.my_table"

  Scenario: Manage duplicate records during load
    Given a Parquet file containing duplicate records at "s3://your-bucket/output/duplicate_data.parquet"
    When the data loading process is executed
    Then duplicates are handled according to business rules
