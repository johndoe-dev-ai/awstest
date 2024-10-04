import json
import boto3
from botocore.exceptions import ClientError

def load_json_to_dynamodb(json_file, table_name):
    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    
    # Load the DynamoDB table
    table = dynamodb.Table(table_name)
    
    # Open the JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Iterate through each item in the JSON file
    for item in data:
        try:
            # Insert item into DynamoDB table
            table.put_item(Item=item)
            print(f"Inserted: {item}")
        except ClientError as e:
            print(f"Failed to insert {item}. Error: {e.response['Error']['Message']}")
    
    print("Data loaded successfully.")

# Usage example
# Replace 'your-json-file.json' with the path to your JSON file and 'YourDynamoDBTable' with the table name
load_json_to_dynamodb('your-json-file.json', 'YourDynamoDBTable')
