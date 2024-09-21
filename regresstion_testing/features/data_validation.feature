Feature: Data Validation

  Scenario: Validate correct processing of valid data
    Given a CSV file with valid data in S3 at "s3://your-bucket/valid_data.csv"
    When the data validation process is executed
    Then the data passes validation without errors

  Scenario: Ensure invalid data is identified
    Given a CSV file with invalid data entries at "s3://your-bucket/invalid_data.csv"
    When the data validation process is executed
    Then the invalid data entries are flagged and logged appropriately
