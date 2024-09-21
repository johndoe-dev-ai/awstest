from behave import given, when, then
import boto3
import pandas as pd
import io
import logging

s3_client = boto3.client('s3')

def upload_data_to_s3(data, bucket, key):
    s3_client.put_object(Bucket=bucket, Key=key, Body=data)
    logging.info(f"Uploaded data to s3://{bucket}/{key}")

def download_data_from_s3(bucket, key):
    response = s3_client.get_object(Bucket=bucket, Key=key)
    data = response['Body'].read().decode('utf-8')
    logging.info(f"Downloaded data from s3://{bucket}/{key}")
    return data

def parse_s3_path(s3_path):
    path = s3_path.replace("s3://", "")
    bucket, key = path.split("/", 1)
    return bucket, key

@given('a CSV file with valid data in S3 at "{s3_path}"')
def step_given_valid_csv_in_s3(context, s3_path):
    bucket, key = parse_s3_path(s3_path)
    data = """id,name,age
            1,Alice,30
            2,Bob,25
            3,Charlie,35
            """
    upload_data_to_s3(data, bucket, key)
    context.s3_bucket = bucket
    context.s3_key = key

@given('a CSV file with invalid data entries at "{s3_path}"')
def step_given_invalid_csv_in_s3(context, s3_path):
    bucket, key = parse_s3_path(s3_path)
    data = """id,name,age
            1,Alice,
            2,Bob,twenty-five
            3,,35
            """
    upload_data_to_s3(data, bucket, key)
    context.s3_bucket = bucket
    context.s3_key = key

@when('the data validation process is executed')
def step_when_data_validation_executed(context):
    bucket = context.s3_bucket
    key = context.s3_key
    data = download_data_from_s3(bucket, key)
    df = pd.read_csv(io.StringIO(data))

    # Simple validation checks
    validation_errors = []
    if df.isnull().values.any():
        validation_errors.append("Missing values detected.")

    try:
        df['age'] = df['age'].astype(int)
    except ValueError:
        validation_errors.append("Invalid data types detected in 'age' column.")

    context.validation_errors = validation_errors

@then('the data passes validation without errors')
def step_then_data_passes_validation(context):
    assert not context.validation_errors, f"Validation errors found: {context.validation_errors}"

@then('the invalid data entries are flagged and logged appropriately')
def step_then_invalid_data_flagged(context):
    assert context.validation_errors, "No validation errors found when expected."
    logging.info(f"Validation errors: {context.validation_errors}")
