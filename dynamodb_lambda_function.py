# dynamodb_lambda_function.py

import boto3
from botocore.exceptions import ClientError
import json

def lambda_handler(event, context):
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    
    # Get table name and item ID from the event
    table_name = event.get('table_name')
    item_id = event.get('item_id')
    
    # Validate input
    if not table_name or not item_id:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing table_name or item_id in the event')
        }
    
    # Get the table
    table = dynamodb.Table(table_name)
    
    try:
        # Attempt to retrieve the item from the table
        response = table.get_item(
            Key={
                'id': item_id
            }
        )
        
        # Check if the item was found
        if 'Item' in response:
            return {
                'statusCode': 200,
                'body': json.dumps(response['Item'])
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps('Item not found')
            }
    
    except ClientError as e:
        # Handle specific DynamoDB exceptions
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return {
                'statusCode': 404,
                'body': json.dumps('Table not found')
            }
        elif e.response['Error']['Code'] == 'ValidationException':
            return {
                'statusCode': 400,
                'body': json.dumps('Validation error: ' + str(e))
            }
        else:
            # Generic error handling
            return {
                'statusCode': 500,
                'body': json.dumps('Error: ' + str(e))
            }
    
    except Exception as e:
        # Catch-all for any other exceptions
        return {
            'statusCode': 500,
            'body': json.dumps('Unexpected error: ' + str(e))
        }
