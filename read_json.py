import json
import boto3

def read_json_from_s3(bucket_name, file_key):
    """
    Reads a JSON file from the specified S3 bucket and key.
    Converts the JSON content into a Python dictionary that can be used as a Lambda event payload.

    :param bucket_name: The name of the S3 bucket
    :param file_key: The key (file path) of the JSON file in the bucket
    :return: The JSON data as a Python dictionary, ready to be used as Lambda event payload
    """
    
    # Initialize the S3 client
    s3 = boto3.client('s3')
    
    try:
        # Get the object from S3
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        
        # Read the content of the file (S3 returns the content as bytes)
        json_data = response['Body'].read().decode('utf-8')
        
        # Convert the JSON string to a Python dictionary
        data = json.loads(json_data)
        
        # Prepare the event payload, you can modify the structure here if needed
        event_payload = {
            "Records": data  # If the JSON data is an array or list of records
        }
        
        return event_payload

    except Exception as e:
        print(f"Error reading file from S3: {str(e)}")
        return None

# Example usage
bucket_name = 'your-bucket-name'
file_key = 'path/to/your/jsonfile.json'

# Call the function to read the JSON from S3 and convert it
event_payload = read_json_from_s3(bucket_name, file_key)

if event_payload:
    print("Event Payload Ready:")
    print(json.dumps(event_payload, indent=4))  # Pretty print the payload
