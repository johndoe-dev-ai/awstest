import json
import boto3
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    # Use a hard-coded DynamoDB table name
    table_name = "S3ArchivalConfigurations"

    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    # Scan parameters
    scan_kwargs = {
        "FilterExpression": Attr('Active').eq(True)
    }
    
    items = []
    done = False
    start_key = None

    # Loop until all pages are scanned
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key

        response = table.scan(**scan_kwargs)
        items.extend(response.get('Items', []))
        
        start_key = response.get('LastEvaluatedKey', None)
        if not start_key:
            done = True

    # Return the items in a structure that Step Functions can consume.
    return {
        "rules": items
    }
