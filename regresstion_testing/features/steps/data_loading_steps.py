from behave import given, when, then
import boto3
import pandas as pd
import io
import logging
import psycopg2

s3_client = boto3.client('s3')

# Redshift connection details
redshift_config = {
    'dbname': 'your_db',
    'user': 'your_user',
    'password': 'your_password',
    'host': 'your_redshift_cluster_endpoint',
    'port': '5439'
}

@given('a valid Parquet file in S3 at "{s3_parquet_path}"')
def step_given_parquet_in_s3(context, s3_parquet_path):
    # Assume the Parquet file exists from previous steps
    context.s3_parquet_path = s3_parquet_path

@given('a Parquet file containing duplicate records at "{s3_parquet_path}"')
def step_given_duplicate_parquet_in_s3(context, s3_parquet_path):
    bucket, key = parse_s3_path(s3_parquet_path)
    data = {
        'id': [1, 2, 2],
        'name': ['Alice', 'Bob', 'Bob'],
        'age': [30, 25, 25]
    }
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    s3_client.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
    logging.info(f"Uploaded duplicate Parquet data to s3://{bucket}/{key}")
    context.s3_parquet_path = s3_parquet_path

@when('the data loading process is executed')
def step_when_data_loading_executed(context):
    bucket, key = parse_s3_path(context.s3_parquet_path)

    # Connect to Redshift
    conn = psycopg2.connect(**redshift_config)
    cursor = conn.cursor()

    # Empty the target table
    cursor.execute("TRUNCATE TABLE public.my_table;")

    # Define the COPY command
    copy_command = f"""
    COPY public.my_table
    FROM 's3://{bucket}/{key}'
    IAM_ROLE 'arn:aws:iam::your_account_id:role/your_redshift_role'
    FORMAT AS PARQUET;
    """

    # Execute the COPY command
    cursor.execute(copy_command)
    conn.commit()
    cursor.close()
    conn.close()
    logging.info("Data loaded into Redshift.")

@then('the data is accurately loaded into the Redshift table "{table_name}"')
def step_then_data_in_redshift(context, table_name):
    # Connect to Redshift
    conn = psycopg2.connect(**redshift_config)
    cursor = conn.cursor()

    # Verify data
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    assert count > 0, f"No data found in {table_name}."

@then('duplicates are handled according to business rules')
def step_then_duplicates_handled(context):
    # For example, ensure no duplicates exist in the table
    conn = psycopg2.connect(**redshift_config)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, COUNT(*)
    FROM public.my_table
    GROUP BY id
    HAVING COUNT(*) > 1;
    """)
    duplicates = cursor.fetchall()
    cursor.close()
    conn.close()

    assert not duplicates, f"Duplicate records found: {duplicates}"
