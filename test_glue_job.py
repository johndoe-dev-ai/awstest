import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch
import pandas as pd
import io
import pyarrow.parquet as pq

# Import the function to be tested
from glue_job import convert_csv_to_parquet

@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_aws():
        yield boto3.client('s3', region_name='us-east-1')

@pytest.fixture(scope='function')
def glue_context():
    with patch('awsglue.context.GlueContext') as mock_glue_context:
        yield mock_glue_context.return_value

def create_csv_file():
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def test_convert_csv_to_parquet(s3, glue_context):
    # Set up test data
    raw_bucket = 'raw-bucket'
    raw_key = 'input/data.csv'
    prep_bucket = 'prep-bucket'
    prep_key = 'output/data.parquet'
    
    # Create buckets
    s3.create_bucket(Bucket=raw_bucket)
    s3.create_bucket(Bucket=prep_bucket)
    
    # Upload test CSV file
    csv_content = create_csv_file()
    s3.put_object(Bucket=raw_bucket, Key=raw_key, Body=csv_content)
    
    # Mock GlueContext methods
    mock_dynamic_frame = glue_context.create_dynamic_frame.from_options.return_value
    
    # Call the function
    convert_csv_to_parquet(glue_context, raw_bucket, raw_key, prep_bucket, prep_key)
    
    # Assert that the correct methods were called
    glue_context.create_dynamic_frame.from_options.assert_called_once_with(
        format_options={"quoteChar": '"', "withHeader": True, "separator": ","},
        connection_type="s3",
        format="csv",
        connection_options={
            "paths": [f"s3://{raw_bucket}/{raw_key}"],
            "recurse": True,
        },
        transformation_ctx="datasource0",
    )
    
    glue_context.write_dynamic_frame.from_options.assert_called_once_with(
        frame=mock_dynamic_frame,
        connection_type="s3",
        format="parquet",
        connection_options={
            "path": f"s3://{prep_bucket}/{prep_key}",
            "partitionKeys": [],
        },
        transformation_ctx="datasink1",
    )
    
    # Optionally, verify the Parquet file content
    # Note: This part is commented out because moto doesn't actually create the Parquet file
    # In a real scenario, you might want to download and verify the Parquet file
    
    # response = s3.get_object(Bucket=prep_bucket, Key=prep_key)
    # parquet_content = response['Body'].read()
    # parquet_file = io.BytesIO(parquet_content)
    # parquet_df = pq.read_table(parquet_file).to_pandas()
    # 
    # assert len(parquet_df) == 3
    # assert list(parquet_df.columns) == ['id', 'name', 'age']
