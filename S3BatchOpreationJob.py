import boto3
from datetime import datetime, timedelta, timezone

# Initialize AWS clients
dynamodb = boto3.client('dynamodb')
s3control = boto3.client('s3control')
sts = boto3.client('sts')

# Retrieve the number of days to archive from DynamoDB
def get_number_of_days_to_archive(table_name, key):
    response = dynamodb.get_item(TableName=table_name, Key=key)
    return int(response['Item']['numberOfDaysToArchive']['N'])

# Create an S3 Batch Operations job to tag objects
def create_batch_job(source_bucket, role_arn, report_bucket, days_to_archive, account_id):
    # Calculate the cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_archive)

    # Create the batch job with S3JobManifestGenerator
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
                'Filter': {
                    'CreatedAfter': datetime(1970, 1, 1, tzinfo=timezone.utc),  # Unix epoch start
                    'CreatedBefore': cutoff_date
                }
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
        ClientRequestToken='unique-token',  # Ensure this is unique for idempotency
        Description='Tagging objects as ArchiveEligible=true'
    )
    return response['JobId']

# Monitor the batch job until completion
def monitor_batch_job(job_id, account_id):
    while True:
        response = s3control.describe_job(AccountId=account_id, JobId=job_id)
        status = response['Job']['Status']
        if status in ['Complete', 'Failed', 'Cancelled']:
            return status
        time.sleep(30)  # Wait before polling again

def main():
    # Configuration
    dynamodb_table = 'YourDynamoDBTable'
    dynamodb_key = {'YourPrimaryKey': {'S': 'YourPrimaryKeyValue'}}
    source_bucket = 'your-source-bucket'
    report_bucket = 'your-report-bucket'
    role_arn = 'arn:aws:iam::your-account-id:role/YourBatchOperationsRole'

    # Get the current AWS account ID
    account_id = sts.get_caller_identity()['Account']

    # Step 1: Retrieve the number of days to archive from DynamoDB
    days_to_archive = get_number_of_days_to_archive(dynamodb_table, dynamodb_key)

    # Step 2: Create an S3 Batch Operations job to tag objects
    job_id = create_batch_job(source_bucket, role_arn, report_bucket, days_to_archive, account_id)
    print(f'Batch job created with Job ID: {job_id}')

    # Step 3: Monitor the batch job until completion
    job_status = monitor_batch_job(job_id, account_id)
    print(f'Batch job completed with status: {job_status}')

if __name__ == '__main__':
    main()
