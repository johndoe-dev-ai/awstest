import boto3
import zipfile
import io
import os

def lambda_handler(event, context):
    # Initialize S3 client
    s3 = boto3.client('s3')
    
    # S3 bucket and object key for the zip file
    source_bucket = 'your-source-bucket-name'
    zip_key = 'path/to/your/zipfile.zip'
    
    # Destination folder for CSV files
    dest_folder = 'path/to/destination/folder/'
    
    # Download the zip file from S3
    zip_obj = s3.get_object(Bucket=source_bucket, Key=zip_key)
    buffer = io.BytesIO(zip_obj['Body'].read())
    
    # Open the zip file
    with zipfile.ZipFile(buffer) as zip_ref:
        # Iterate through all the files in the zip
        for filename in zip_ref.namelist():
            if filename.endswith('.csv'):
                # Read the file contents
                file_content = zip_ref.read(filename)
                
                # Upload the file to S3
                dest_key = os.path.join(dest_folder, os.path.basename(filename))
                s3.put_object(Bucket=source_bucket, Key=dest_key, Body=file_content)
    
    return {
        'statusCode': 200,
        'body': 'Successfully unzipped and uploaded CSV files'
    }
