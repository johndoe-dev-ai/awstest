from behave import given, when, then
import boto3
import pandas as pd
import io
import logging
import time

s3_client = boto3.client('s3')

# Reuse helper functions from previous steps

@given('a large CSV file in S3 at "{s3_path}"')
def step_given_large_csv_in_s3(context, s3_path):
    bucket, key = parse_s3_path(s3_path)
    data = "id,name,age\n"
    # Generate a large dataset
    for i in range(1, 1000001):
        data += f"{i},User{i},{20 + (i % 30)}\n"
    upload_data_to_s3(data, bucket, key)
    context.s3_bucket = bucket
    context.s3_key = key

@when('the conversion process is triggered')
def step_when_conversion_triggered(context):
    bucket = context.s3_bucket
    key = context.s3_key
    data = download_data_from_s3(bucket, key)
    df = pd.read_csv(io.StringIO(data))

    # Convert to Parquet
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)

    # Upload Parquet file to S3
    parquet_key = key.replace('.csv', '.parquet').replace('input/', 'output/')
    s3_client.put_object(Bucket=bucket, Key=parquet_key, Body=buffer.getvalue())
    logging.info(f"Converted and uploaded Parquet file to s3://{bucket}/{parquet_key}")
    context.parquet_key = parquet_key

@then('a Parquet file is generated at "{s3_parquet_path}" with data matching the original CSV')
def step_then_parquet_generated(context, s3_parquet_path):
    bucket, key = parse_s3_path(s3_parquet_path)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    parquet_data = response['Body'].read()

    # Read Parquet file
    df_parquet = pd.read_parquet(io.BytesIO(parquet_data))

    # Read original CSV for comparison
    csv_data = download_data_from_s3(context.s3_bucket, context.s3_key)
    df_csv = pd.read_csv(io.StringIO(csv_data))

    # Compare dataframes
    assert df_parquet.equals(df_csv), "Parquet data does not match original CSV data."

@then('the Parquet file is generated without performance degradation')
def step_then_performance_ok(context):
    # This would have been timed in the @when step
    # For demonstration, let's assume we have the time recorded
    # We'll simulate checking that the conversion took less than a threshold
    conversion_time = context.conversion_time  # Assume this was set during conversion
    threshold = 300  # seconds
    assert conversion_time < threshold, f"Conversion took too long: {conversion_time} seconds"
