import boto3
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


def update_or_create_lifecycle_rule(bucket, prefix, storage_class, days_to_archive):
    """
    Update an existing S3 lifecycle rule if it exists, or create a new one.
    """
    rule_id = f"{prefix.replace('/', '-')}-deep-archive"

    try:
        # Get the existing lifecycle configuration
        existing_config = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket)
        rules = existing_config.get("Rules", [])
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            rules = []  # No existing rules
        else:
            print(f"Error fetching lifecycle configuration for {bucket}: {e}")
            return

    rule_exists = False
    updated_rules = []

    # Check for existing rule and update if found
    for rule in rules:
        if rule['ID'] == rule_id:
            rule['Filter'] = {'Prefix': prefix}
            rule['Transitions'] = [{
                'Days': days_to_archive,
                'StorageClass': storage_class
            }]
            rule['Status'] = 'Enabled'
            rule_exists = True
            print(f"Updating existing rule: {rule_id}")
        updated_rules.append(rule)

    # Add new rule if not exists
    if not rule_exists:
        print(f"Creating new lifecycle rule: {rule_id}")
        updated_rules.append({
            'ID': rule_id,
            'Filter': {'Prefix': prefix},
            'Status': 'Enabled',
            'Transitions': [
                {
                    'Days': days_to_archive,
                    'StorageClass': storage_class
                }
            ]
        })

    # Update the lifecycle configuration
    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration={'Rules': updated_rules}
        )
        print(f"Lifecycle configuration updated successfully for bucket '{bucket}'.")
    except ClientError as e:
        print(f"Error updating lifecycle configuration for {bucket}: {e}")


def main():
    configs = get_active_archival_configs(DYNAMODB_TABLE_NAME)

    for config in configs:
        try:
            job_group_name = config['JobGroupName']
            bucket = config['SourceBucket']
            prefix = config['ExtractUnloadPath']
            days_to_archive = int(config['NoOfDaysToArchival'])
            storage_class = config['StorageClass']

            print(f"Processing Job Group: {job_group_name}")
            update_or_create_lifecycle_rule(bucket, prefix, storage_class, days_to_archive)

        except KeyError as e:
            print(f"Missing configuration key: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
