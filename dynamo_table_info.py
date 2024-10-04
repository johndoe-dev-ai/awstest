import json
import boto3
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    # Initialize a DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    
    # Specify the DynamoDB table name
    table_name = 'test_reference'
    table = dynamodb.Table(table_name)
    
    # Query the table for items with source='abc' and job='cde'
    try:
        response = table.query(
            KeyConditionExpression=Key('source').eq('abc') & Key('job').eq('cde')
        )
        
        # Fetch the items
        items = response.get('Items', [])
        
        # Return a success response with the fetched items
        return {
            'statusCode': 200,
            'body': json.dumps(items)
        }
        
    except Exception as e:
        # Return an error response if something went wrong
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error fetching data: {str(e)}")
        }
