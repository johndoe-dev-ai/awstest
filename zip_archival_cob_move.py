import boto3
import re
import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# AWS Clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration
DYNAMODB_TABLE_NAME = "S3ArchivalConfigurations"

def get_active_archival_configs(table_name):
    """
    Fetch all active archival configurations from DynamoDB.
    """
    table = dynamodb.Table(table_name)
    try:
        response = table.scan(
            FilterExpression=Key('Active').eq(True)
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error fetching archival configurations: {e}")
        return []

def extract_cob_date_from_filename(filename, pattern):
    """
    Extract COB date from filename using the provided pattern.
    """
    match = re.search(pattern, filename)
    if match:
        try:
            cob_date = datetime.datetime.strptime(match.group(), "%Y%m%d")
            return cob_date
        except ValueError as e:
            print(f"Error parsing COB date: {e}")
    return None

def list_objects_to_archive(bucket, prefix, file_extensions, cob_date_pattern, days_to_archive):
    """
    List S3 objects matching the prefix and determine if they are eligible for archival.
    """
    objects_to_archive = []
    current_date = datetime.datetime.utcnow()

    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if any(key.endswith(ext) for ext in file_extensions):
                filename = key.split('/')[-1]
                cob_date = extract_cob_date_from_filename(filename, cob_date_pattern)
                if cob_date:
                    age_days = (current_date - cob_date).days
                    if age_days > days_to_archive:
                        objects_to_archive.append(obj)
    return objects_to_archive

def move_to_deep_archive(source_bucket, object_key, target_bucket, storage_class):
    """
    Copy an object to the target bucket with specified storage class, then delete from source.
    """
    try:
        copy_source = {'Bucket': source_bucket, 'Key': object_key}
        s3_client.copy_object(
            Bucket=target_bucket,
            Key=object_key,
            CopySource=copy_source,
            StorageClass=storage_class
        )
        print(f"Successfully archived {object_key} to {target_bucket} with {storage_class}")
        # Delete from source bucket
        s3_client.delete_object(Bucket=source_bucket, Key=object_key)
    except ClientError as e:
        print(f"Error archiving object {object_key}: {e}")

def main():
    configs = get_active_archival_configs(DYNAMODB_TABLE_NAME)

    for config in configs:
        try:
            job_group_name = config['JobGroupName']
            bucket = config['SourceBucket']
            prefix = config['ExtractUnloadPath']
            file_extensions = config['ArchivalRuleReferenceAttributes']['AllowedFileExtensions']
            cob_date_pattern = config['ArchivalRuleReferenceAttributes']['COBDatePattern']
            days_to_archive = int(config['NoOfDaysToArchival'])
            target_bucket = config.get('TargetBucket', bucket)  # Use source bucket if target not provided
            storage_class = config['StorageClass']

            print(f"Processing Job Group: {job_group_name}")
            objects_to_archive = list_objects_to_archive(bucket, prefix, file_extensions, cob_date_pattern, days_to_archive)

            for obj in objects_to_archive:
                move_to_deep_archive(bucket, obj['Key'], target_bucket, storage_class)

        except KeyError as e:
            print(f"Missing configuration key: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
