Feature: Data Transformation

  Scenario: Convert CSV to Parquet successfully
    Given a valid CSV file in S3 at "s3://your-bucket/valid_data.csv"
    When the conversion process is triggered
    Then a Parquet file is generated at "s3://your-bucket/output/valid_data.parquet" with data matching the original CSV

  Scenario: Handle large CSV files efficiently
    Given a large CSV file in S3 at "s3://your-bucket/large_data.csv"
    When the conversion process is triggered
    Then the Parquet file is generated without performance degradation
