import boto3
import os
import time
from datetime import datetime, timedelta, timezone

def lambda_handler(event, context):
    # Initialize AWS clients
    dynamodb = boto3.client('dynamodb')
    s3control = boto3.client('s3control')
    sts = boto3.client('sts')

    # Configuration
    dynamodb_table = os.getenv('DYNAMODB_TABLE', 'YourDynamoDBTable')
    dynamodb_key = {'YourPrimaryKey': {'S': os.getenv('DYNAMODB_PRIMARY_KEY', 'YourPrimaryKeyValue')}}
    source_bucket = os.getenv('SOURCE_BUCKET', 'your-source-bucket')
    report_bucket = os.getenv('REPORT_BUCKET', 'your-report-bucket')
    role_arn = os.getenv('ROLE_ARN', 'arn:aws:iam::your-account-id:role/YourBatchOperationsRole')

    # Get the current AWS account ID
    account_id = sts.get_caller_identity()['Account']

    # Retrieve optional filters from DynamoDB
    def get_filters():
        try:
            response = dynamodb.get_item(TableName=dynamodb_table, Key=dynamodb_key)
            item = response.get('Item', {})
            prefix = item.get('Prefix', {}).get('S')
            suffix = item.get('Suffix', {}).get('S')
            substring = item.get('Substring', {}).get('S')
            days_to_archive = int(item['numberOfDaysToArchive']['N'])
            return prefix, suffix, substring, days_to_archive
        except Exception as e:
            print(f"Error retrieving filters: {e}")
            raise

    prefix, suffix, substring, days_to_archive = get_filters()

    # Calculate the cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_archive)

    # Create an S3 Batch Operations job
    def create_batch_job():
        try:
            filter_criteria = {'CreatedAfter': datetime(1970, 1, 1, tzinfo=timezone.utc), 'CreatedBefore': cutoff_date}

            # Add optional filters
            if prefix:
                filter_criteria['ObjectKeyPrefix'] = prefix
            if suffix:
                filter_criteria['ObjectKeySuffix'] = suffix
            if substring:
                filter_criteria['ObjectKeySubstring'] = substring

            response = s3control.create_job(
                AccountId=account_id,
                Operation={
                    'PutObjectTagging': {
                        'TagSet': [
                            {
                                'Key': 'ArchiveEligible',
                                'Value': 'true'
                            }
                        ]
                    }
                },
                ManifestGenerator={
                    'S3JobManifestGenerator': {
                        'ExpectedBucketOwner': account_id,
                        'SourceBucket': source_bucket,
                        'ManifestOutputLocation': {
                            'Bucket': f'arn:aws:s3:::{report_bucket}',
                            'Prefix': 'manifests/'
                        },
                        'Filter': filter_criteria
                    }
                },
                Report={
                    'Bucket': f'arn:aws:s3:::{report_bucket}',
                    'Format': 'Report_CSV_20180820',
                    'Enabled': True,
                    'Prefix': 'batch-reports',
                    'ReportScope': 'AllTasks'
                },
                Priority=1,
                RoleArn=role_arn,
                ClientRequestToken='unique-token',
                Description='Tagging objects as ArchiveEligible=true'
            )
            return response['JobId']
        except Exception as e:
            print(f"Error creating batch job: {e}")
            raise

    job_id = create_batch_job()
    print(f"Batch job created with Job ID: {job_id}")

    # Monitor the batch job until completion
    def monitor_batch_job(job_id):
        while True:
            response = s3control.describe_job(AccountId=account_id, JobId=job_id)
            status = response['Job']['Status']
            if status in ['Complete', 'Failed', 'Cancelled']:
                return status
            time.sleep(30)

    job_status = monitor_batch_job(job_id)
    print(f"Batch job completed with status: {job_status}")

    return {
        'statusCode': 200,
        'body': {
            'JobId': job_id,
            'Status': job_status
        }
    }
