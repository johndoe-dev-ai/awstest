import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# AWS Clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration
DYNAMODB_TABLE_NAME = "S3ArchivalConfigurations"


def get_active_archival_configs(table_name):
    """
    Fetch all active archival configurations from DynamoDB where ObjectType is 'zip'.
    Handles pagination in case of large datasets.
    """
    table = dynamodb.Table(table_name)
    configs = []

    try:
        response = table.scan(
            FilterExpression=Key('Active').eq(True) & Attr('ObjectType').eq('zip')
        )
        configs.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=Key('Active').eq(True) & Attr('ObjectType').eq('zip'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            configs.extend(response.get('Items', []))

        return configs
    except ClientError as e:
        print(f"Error fetching archival configurations: {e}")
        return []


def update_or_create_lifecycle_rule(bucket, prefix, storage_class, days_to_archive, tag_filter_required, days_to_expire, noncurrent_days_to_expire):
    """
    Update an existing S3 lifecycle rule if it exists, or create a new one.
    Handles current and noncurrent versions of objects.
    Adds a tag filter if TagFilterRequired is True.
    Adds expiration logic if NoOfDaysToExpire and NoncurrentVersionExpireDays are specified.
    """
    rule_id = f"{prefix.replace('/', '-').replace('_', '-')}-deep-archive"

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

    # Define the filter
    filter_definition = {'Prefix': prefix}
    if tag_filter_required:
        filter_definition = {
            'And': {
                'Prefix': prefix,
                'Tags': [
                    {'Key': 'ArchiveEligible', 'Value': 'true'}
                ]
            }
        }

    # Build the base rule structure
    new_rule = {
        'ID': rule_id,
        'Filter': filter_definition,
        'Status': 'Enabled',
        'Transitions': [
            {
                'Days': days_to_archive,
                'StorageClass': storage_class
            }
        ],
        'NoncurrentVersionTransitions': [
            {
                'NoncurrentDays': days_to_archive,
                'StorageClass': storage_class
            }
        ]
    }

    # Add expiration logic if specified
    if days_to_expire:
        new_rule['Expiration'] = {'Days': days_to_expire}
    if noncurrent_days_to_expire:
        new_rule['NoncurrentVersionExpiration'] = {
            'NoncurrentDays': noncurrent_days_to_expire
        }

    # Check for existing rule and update if found
    for rule in rules:
        if rule['ID'] == rule_id:
            rule.update(new_rule)
            rule_exists = True
            print(f"Updating existing rule: {rule_id}")
        updated_rules.append(rule)

    # Add new rule if not exists
    if not rule_exists:
        print(f"Creating new lifecycle rule: {rule_id}")
        updated_rules.append(new_rule)

    # Update the lifecycle configuration
    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration={'Rules': updated_rules}
        )
        print(f"Lifecycle configuration updated successfully for bucket '{bucket}'.")
    except ClientError as e:
        print(f"Error updating lifecycle configuration for {bucket}: {e}")


def lambda_handler(event, context):
    configs = get_active_archival_configs(DYNAMODB_TABLE_NAME)

    for config in configs:
        try:
            job_group_name = config['JobGroupName']
            bucket = config['SourceBucket']
            prefix = config['ExtractUnloadPath']
            days_to_archive = int(config['NoOfDaysToArchival'])
            storage_class = config['StorageClass']
            tag_filter_required = config.get('TagFilterRequired', False)
            days_to_expire = int(config.get('NoOfDaysToExpire', 0)) or None
            noncurrent_days_to_expire = int(config.get('NoncurrentVersionExpireDays', 0)) or None

            print(f"Processing Job Group: {job_group_name}")
            update_or_create_lifecycle_rule(
                bucket, prefix, storage_class, days_to_archive,
                tag_filter_required, days_to_expire, noncurrent_days_to_expire
            )

        except KeyError as e:
            print(f"Missing configuration key: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
