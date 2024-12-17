import boto3
import logging
import json
from awsglue.utils import getResolvedOptions
import sys

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

args = getResolvedOptions(sys.argv,
                          ['region', 'AccountDetails'])

class LifecycleCreation:
    def __init__(self):
        logger.info("Initializing LifecycleCreation class")
        self.s3_client = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        self.default_rules = ['dmt-wh-raw-LifecycleRule', 'ExpiredObjectDeleteMarker']
        self.raw_bucketName = 'dmt-wh-raw-[AccountDetails]'.replace('[AccountDetails]', account_details)
        logger.info(f"Raw bucket name set to: {self.raw_bucketName}")

    def main(self):
        logger.info("Starting main function")
        table_archive = self.dynamodb.Table('DataLensS3ObjectArchival')
        logger.info("Scanning DynamoDB table: DataLensS3ObjectArchival")
        response_archive_scan = table_archive.scan()
        current_rules = self.current_lcm_rules_def(self.raw_bucketName)
        rule_ids_from_db = self.rule_ids_from_db(response_archive_scan)
        rule_list = []

        for feed in response_archive_scan['Items']:
            logger.info('Currently working for feed: ' + str(feed))
            job_group_name = feed['jobGroupName']
            raw_tag = feed['rawClass']
            raw_transition = feed['rawTransition']
            raw_expiration = feed['rawExpiration']
            raw_prefix = feed['rawSource']
            prep_archival = feed['prepArchival']
            logger.info(f"Fetching objects for prefix: {raw_prefix}")
            object_arr = self.get_all_obj(self.raw_bucketName, raw_prefix)
            logger.info(f"Checking tags for {len(object_arr)} objects")
            object_arr = self.check_tag(self.raw_bucketName, object_arr, raw_tag, raw_transition, raw_expiration)
            logger.info(f"Adding lifecycle rule for JobGroupName: {job_group_name}")
            rule_list.append((raw_tag, raw_transition, raw_expiration))

        rule_set = set(rule_list)
        rule_list = list(rule_set)
        logger.info(f"Unique rules extracted: {rule_list}")
        new_rules = []

        logger.info('Creating List of unique rules that has to be created for the bucket')
        for rule in rule_list:
            new_rules.append(self.create_lcm_rule(rule[0], rule[1], rule[2]))

        logger.info("Creating and updating bucket lifecycle configuration")
        self.create_lcm(self.raw_bucketName, current_rules, self.default_rules, new_rules, rule_ids_from_db)
        logger.info("Main function execution completed")

    def get_all_obj(self, bucketName, prefix):
        logger.info(f'Getting all objects for prefix: {prefix}')
        object_arr = []
        ContinuationToken = 'NA'
        while(True):
            logger.info("Fetching objects using S3 list_objects_v2 API")
            if ContinuationToken == 'NA':
                response = self.s3_client.list_objects_v2(
                    Bucket=bucketName,
                    Prefix=prefix
                )
            else:
                response = self.s3_client.list_objects_v2(
                    Bucket=bucketName,
                    Prefix=prefix,
                    ContinuationToken=ContinuationToken
                )
            
            if not (str(response.get('Contents')) == 'None' or response.get('Contents') == ''):
                object_arr = object_arr + response['Contents']

            if response['IsTruncated'] is False:
                logger.info("No more objects to fetch")
                break

            ContinuationToken = response['NextContinuationToken']
            logger.info('More than 1000 objects received, fetching next batch')

        logger.info(f"Total objects fetched: {len(object_arr)}")
        for item in object_arr:
            if item['Key'].split('.')[-1] not in ['zip', 'done']:
                object_arr.remove(item)
        
        logger.info(f"Objects remaining after filtering: {len(object_arr)}")
        return object_arr

    def check_tag(self, bucketName, object_arr, tag, transition, expiration):
        logger.info('Checking if tags are present in objects')
        for item in object_arr:
            logger.info(f"Checking tags for object: {item['Key']}")
            response = self.s3_client.get_object_tagging(
                Bucket=bucketName,
                Key=item['Key']
            )
            tag_present = 0
            for obj in response['TagSet']:
                if obj['Key'] == 'class' and obj['Value'] == f'{tag}-{transition}-{expiration}':
                    tag_present += 1
            if tag_present == 0:
                logger.info(f"Tag missing, tagging object: {item['Key']}")
                self.tag_object(bucketName, item['Key'], tag, transition, expiration)
        logger.info("Tag check completed")
        return object_arr

    def tag_object(self, bucketName, key, tag, transition, expiration):
        logger.info(f"Tagging object {key} with {tag}-{transition}-{expiration}")
        self.s3_client.put_object_tagging(
            Bucket=bucketName,
            Key=key,
            Tagging={
                'TagSet': [
                    {
                        'Key': 'Class',
                        'Value': f'{tag}-{transition}-{expiration}'
                    }
                ]
            }
        )

    def current_lcm_rules_def(self, bucket_name):
        logger.info(f"Fetching current lifecycle rules for bucket: {bucket_name}")
        try:
            lcm_rules = self.s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)['Rules']
        except Exception as e:
            logger.warning(f"No existing LCM in bucket {bucket_name}, error: {e}")
            lcm_rules = []
        logger.info(f"Current LCM rules: {lcm_rules}")
        return lcm_rules

    def create_lcm_rule(self, tag, transition, expiration):
        logger.info(f"Creating lifecycle rule for tag: {tag}, transition: {transition}, expiration: {expiration}")
        rule = """
        {
            "Expiration": {"Days": "%s"},
            "ID": "JobGroupName-lifecycle",
            "Filter": {
                "Tag": {
                    "Key": "Class",
                    "Value": "%s"
                }
            },
            "Status": "Enabled",
            "Transitions": [
                {
                    "Days": %s,
                    "StorageClass": "DEEP_ARCHIVE"
                }
            ]
        }
        """ % (expiration, tag, transition)

        rule = json.loads(rule)
        rule['Filter']['Tag']['Value'] = f'{tag}-{transition}-{expiration}'
        rule['Transitions'][0]['Days'] = int(transition)
        rule['Expiration']['Days'] = int(expiration)
        rule['Transitions'][0]['StorageClass'] = tag
        rule['ID'] = f'dmt-{tag}-{transition}-{expiration}-lifecycle'
        logger.info(f"Lifecycle rule created: {rule}")
        return rule

    def create_lcm(self, bucket_name, current_rules, default_rules, new_rules, rule_ids_from_db):
        logger.info(f'Creating LCM configuration for bucket: {bucket_name}')
        required_rules = []
        for rule in current_rules:
            if rule['ID'] in default_rules or rule['ID'] in rule_ids_from_db:
                required_rules.append(rule)
        for rule in new_rules:
            if rule not in required_rules:
                required_rules.append(rule)
        logger.info(f"Final set of lifecycle rules: {required_rules}")
        self.s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                'Rules': required_rules
            })
        logger.info("Lifecycle configuration updated successfully")

    def rule_ids_from_db(self, response_archive_scan):
        logger.info("Extracting rule IDs from DynamoDB")
        rule_ids = set()
        for row in response_archive_scan['Items']:
            rule_id_raw = 'dlt-' + row.get('rawClass') + '-' + str(row.get('rawTransition')) + '-' + str(row.get('rawExpiration')) + '-lifecycle'
            rule_id_processed = 'dlt-' + str(row.get('processedClass')) + '-' + str(row.get('processedTransition')) + '-' + str(row.get('processedExpiration'))
            rule_ids.add(rule_id_raw)
            if not (str(row.get('processedClass')) == 'None' or str(row.get('processedClass')) == ""):
                rule_ids.add(rule_id_processed)
        logger.info(f"Rule IDs extracted: {rule_ids}")
        return list(rule_ids)

if __name__ == "__main__":
    logger.info("Starting script execution")
    account_details = args['AccountDetails']
    logger.info(f"Account details received: {account_details}")
    LifecycleCreation = LifecycleCreation()
    LifecycleCreation.main()
    logger.info("Script execution completed")
