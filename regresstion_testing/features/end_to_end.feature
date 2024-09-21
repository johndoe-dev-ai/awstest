Feature: End-to-End Data Pipeline

  Scenario: Full pipeline success
    Given a valid CSV file in S3 at "s3://your-bucket/valid_data.csv"
    When the full data pipeline is executed
    Then the data is available in Redshift with accurate records

  Scenario: Pipeline handles errors gracefully
    Given a CSV file with some invalid data in S3 at "s3://your-bucket/invalid_data.csv"
    When the full data pipeline is executed
    Then invalid data is logged and skipped, while valid data is processed and loaded
