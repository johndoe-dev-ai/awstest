import boto3
import zipfile
import io
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function to unzip files from S3 bucket's compressed folder 
    and place them in uncompressed folder.
    
    Args:
        event: AWS Lambda event object
        context: AWS Lambda context object
        
    Returns:
        Dict containing status and processing details
    """
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    try:
        # Get bucket and key information
        bucket_name = os.environ.get('BUCKET_NAME')  # Set this in Lambda environment variables
        compressed_prefix = 'compressed/'
        uncompressed_prefix = 'uncompressed/'
        
        # List all objects in compressed folder
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=compressed_prefix
        )
        
        if 'Contents' not in response:
            return {
                'statusCode': 200,
                'body': 'No files found in compressed folder'
            }
        
        processed_files = []
        
        # Process each zip file
        for obj in response['Contents']:
            # Skip if not a zip file
            if not obj['Key'].endswith('.zip'):
                continue
                
            # Get the zip file from S3
            zip_obj = s3_client.get_object(
                Bucket=bucket_name,
                Key=obj['Key']
            )
            
            # Read the zip file content
            zip_content = io.BytesIO(zip_obj['Body'].read())
            
            # Process the zip file
            with zipfile.ZipFile(zip_content) as zip_ref:
                # Extract each file in the zip
                for file_name in zip_ref.namelist():
                    # Skip if not a CSV file
                    if not file_name.endswith('.csv'):
                        continue
                        
                    # Read the CSV content
                    csv_content = zip_ref.read(file_name)
                    
                    # Create new key for uncompressed file
                    new_key = f"{uncompressed_prefix}{os.path.basename(file_name)}"
                    
                    # Upload CSV to uncompressed folder
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=new_key,
                        Body=csv_content
                    )
                    
                    processed_files.append({
                        'zip_file': obj['Key'],
                        'extracted_file': new_key
                    })
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Successfully processed zip files',
                'processed_files': processed_files
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error processing zip files: {str(e)}'
        }
