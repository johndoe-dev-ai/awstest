import boto3
import json
import csv
import os
from datetime import datetime, timedelta
from io import StringIO
from awsglue.context import GlueContext
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit

# Initialize Glue Context
glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Entry point for AWS Glue job
def main():
    table_name = 'YourDynamoDBTable'
    bucket = 'your-bucket-name'
    manifest_key = 'your-manifest-key'
    
    table = dynamodb.Table(table_name)
    prefixes, object_types, archive_days = get_dynamodb_filters(table)

    # Load manifest file and get list of data files
    manifest = read_json_manifest(bucket, manifest_key)
    data_files = [file['key'] for file in manifest['files']]

    # Process files and generate new filtered data and manifest
    new_files = []
    for file_key in data_files:
        print(f"Processing: {file_key}")
        df = read_s3_csv(bucket, file_key)
        filtered_df = filter_data(df, prefixes, object_types, archive_days)
        new_file_key = upload_filtered_file(bucket, filtered_df, file_key)
        new_files.append({'Bucket': bucket, 'Key': new_file_key})
    
    # Overwrite existing JSON manifest file
    overwrite_json_manifest(bucket, manifest_key, new_files)
    print("Glue job completed successfully. Files processed and manifest updated.")

def read_json_manifest(bucket, manifest_key):
    """Read and parse a JSON manifest file from S3."""
    response = s3.get_object(Bucket=bucket, Key=manifest_key)
    content = response['Body'].read().decode('utf-8')
    return json.loads(content)

def get_dynamodb_filters(table):
    prefixes = []
    object_types = []
    archive_days = None
    response = table.scan()
    for item in response['Items']:
        if 'prefix' in item:
            prefixes.append(item['prefix'])
        if 'objectType' in item:
            object_types.append(item['objectType'])
        if 'NoOfDaysToArchive' in item:
            archive_days = int(item['NoOfDaysToArchive'])
    return prefixes, object_types, archive_days

def read_s3_csv(bucket, file_key):
    path = f"s3://{bucket}/{file_key}"
    return spark.read.csv(path, header=True)

def filter_data(df, prefixes, object_types, archive_days):
    conditions = []
    if prefixes:
        prefix_condition = col('Key').rlike(f"^({'|'.join(prefixes)})")
        conditions.append(prefix_condition)
    if object_types:
        object_condition = col('ObjectOwner').isin(object_types)
        conditions.append(object_condition)
    if archive_days:
        date_limit = datetime.utcnow() - timedelta(days=archive_days)
        date_condition = col('LastModifiedDate') < lit(date_limit.strftime('%Y-%m-%dT%H:%M:%S'))
        conditions.append(date_condition)
    
    for condition in conditions:
        df = df.filter(condition)
    return df

def upload_filtered_file(bucket, df, original_key):
    new_key = f"processed/{os.path.basename(original_key)}"
    output_path = f"s3://{bucket}/{new_key}"
    df.write.csv(output_path, mode='overwrite', header=True)
    print(f"Filtered file uploaded: {new_key}")
    return new_key

def overwrite_json_manifest(bucket, manifest_key, new_files):
    """Overwrite an existing JSON manifest file with updated file references."""
    new_manifest = {
        "sourceBucket": bucket,
        "files": [{"key": file['Key']} for file in new_files]
    }
    
    manifest_file = '/tmp/updated_manifest.json'
    with open(manifest_file, 'w') as jsonfile:
        json.dump(new_manifest, jsonfile, indent=4)
    
    s3.upload_file(manifest_file, bucket, manifest_key)
    print(f"JSON manifest file overwritten: {manifest_key}")

if __name__ == "__main__":
    main()
