import boto3
import os
import logging
import tempfile
import botocore
from botocore.exceptions import ClientError

# --- Configuration ---
# IMPORTANT: For production, avoid hardcoding credentials.
# Use environment variables, AWS Secrets Manager, or IAM roles for EC2 instances.

# Source S3 Bucket Configuration
SOURCE_AWS_ACCESS_KEY_ID = "YOUR_SOURCE_AWS_ACCESS_KEY_ID"
SOURCE_AWS_SECRET_ACCESS_KEY = "YOUR_SOURCE_AWS_SECRET_ACCESS_KEY"
SOURCE_AWS_REGION = "YOUR_SOURCE_AWS_REGION"
SOURCE_BUCKET_NAME = "your-source-bucket-name"
SOURCE_OBJECT_KEY = "path/to/your/large_file.zip"
# If using a VPC Endpoint, provide its URL here.
# Example: "vpce-0123456789abcdef0-abcdefg.s3.your-source-aws-region.vpce.amazonaws.com"
# If not using a VPC endpoint, set to None.
SOURCE_S3_VPC_ENDPOINT_URL = None # "YOUR_S3_VPC_ENDPOINT_URL_HERE"


# Destination S3 Bucket Configuration
DEST_AWS_ACCESS_KEY_ID = "YOUR_DEST_AWS_ACCESS_KEY_ID"
DEST_AWS_SECRET_ACCESS_KEY = "YOUR_DEST_AWS_SECRET_ACCESS_KEY"
DEST_AWS_REGION = "YOUR_DEST_AWS_REGION"
DEST_BUCKET_NAME = "your-destination-bucket-name"
DEST_OBJECT_KEY = "path/to/new_large_file.zip" # Can be same as SOURCE_OBJECT_KEY

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def create_s3_client(aws_access_key_id, aws_secret_access_key, region_name, endpoint_url=None):
    """
    Creates and returns a boto3 S3 client with specified credentials and region.
    Optionally includes an endpoint URL for VPC endpoints.
    """
    try:
        if endpoint_url:
            client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
                endpoint_url=endpoint_url
            )
            logger.info(f"Created S3 client for region '{region_name}' with endpoint: {endpoint_url}")
        else:
            client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            logger.info(f"Created S3 client for region '{region_name}' (no custom endpoint).")
        return client
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise

def perform_source_recon(s3_client, bucket_name, object_key):
    """
    Performs reconnaissance on the source S3 bucket and object.
    Checks for bucket existence, object existence, and object size/metadata.
    """
    logger.info(f"\n--- Source S3 Reconnaissance for '{bucket_name}/{object_key}' ---")
    try:
        # Check if the source bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Source bucket '{bucket_name}' exists.")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            logger.error(f"Source bucket '{bucket_name}' not found. Please check the bucket name and region.")
        elif error_code == '403':
            logger.error(f"Access denied to source bucket '{bucket_name}'. Check credentials and bucket policy.")
        else:
            logger.error(f"Error checking source bucket '{bucket_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during source bucket check: {e}")
        return False

    try:
        # Check if the source object exists and get its metadata
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        file_size_bytes = response.get('ContentLength', 'N/A')
        file_last_modified = response.get('LastModified', 'N/A')
        logger.info(f"Source object '{object_key}' found.")
        logger.info(f"  Size: {file_size_bytes} bytes")
        logger.info(f"  Last Modified: {file_last_modified}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            logger.error(f"Source object '{object_key}' not found in bucket '{bucket_name}'.")
        elif error_code == '403':
            logger.error(f"Access denied to source object '{object_key}'. Check credentials and object permissions.")
        else:
            logger.error(f"Error checking source object '{object_key}': {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during source object check: {e}")
        return False

def perform_destination_recon(s3_client, bucket_name, object_key):
    """
    Performs reconnaissance on the destination S3 bucket.
    Checks for bucket existence and write permissions.
    """
    logger.info(f"\n--- Destination S3 Reconnaissance for '{bucket_name}/{object_key}' ---")
    try:
        # Check if the destination bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Destination bucket '{bucket_name}' exists.")

        # Attempt a dummy put to check write permissions (optional but good for recon)
        # This is a good way to test permissions without affecting existing data,
        # but could create an empty object if permissions allow.
        # Alternatively, check bucket policy/IAM role for 's3:PutObject'
        try:
            test_key = f"recon_test_permissions_{os.urandom(8).hex()}"
            s3_client.put_object(Bucket=bucket_name, Key=test_key, Body=b'')
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            logger.info(f"Write permissions confirmed for destination bucket '{bucket_name}'.")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'AccessDenied':
                logger.error(f"Access denied to write to destination bucket '{bucket_name}'. Check credentials and bucket policy.")
                return False
            else:
                logger.warning(f"Could not fully confirm write permissions (error: {e}). Proceeding but be aware.")

        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            logger.error(f"Destination bucket '{bucket_name}' not found. Please check the bucket name and region.")
        elif error_code == '403':
            logger.error(f"Access denied to destination bucket '{bucket_name}'. Check credentials and bucket policy.")
        else:
            logger.error(f"Error checking destination bucket '{bucket_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during destination bucket check: {e}")
        return False

def transfer_s3_file(source_s3_client, dest_s3_client,
                     source_bucket, source_key, dest_bucket, dest_key):
    """
    Downloads a large file from source S3 and uploads it to destination S3.
    Uses tempfile for efficient handling of large files without loading into memory.
    """
    logger.info(f"\n--- Starting S3 File Transfer ---")
    logger.info(f"Source: s3://{source_bucket}/{source_key}")
    logger.info(f"Destination: s3://{dest_bucket}/{dest_key}")

    # Use a temporary file to store the downloaded content
    # This is crucial for performance with huge files, avoiding memory issues.
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            logger.info(f"Temporary file created at: {temp_file_path}")

            # Download the file from source S3
            logger.info("Starting download from source S3...")
            source_s3_client.download_file(source_bucket, source_key, temp_file_path)
            logger.info(f"Download complete: {os.path.getsize(temp_file_path)} bytes downloaded.")

            # Upload the file to destination S3
            logger.info("Starting upload to destination S3...")
            dest_s3_client.upload_file(temp_file_path, dest_bucket, dest_key)
            logger.info("Upload complete.")

        logger.info("File transfer successful!")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        logger.error(f"S3 Client Error during transfer: {error_code} - {e}")
        return False
    except FileNotFoundError:
        logger.error(f"Temporary file not found during transfer: {temp_file_path}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during file transfer: {e}")
        return False
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file '{temp_file_path}' cleaned up.")
            except OSError as e:
                logger.warning(f"Error removing temporary file '{temp_file_path}': {e}")


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("--- Starting S3 File Transfer Script ---")

    # 1. Create S3 clients
    try:
        source_s3_client = create_s3_client(
            SOURCE_AWS_ACCESS_KEY_ID,
            SOURCE_AWS_SECRET_ACCESS_KEY,
            SOURCE_AWS_REGION,
            SOURCE_S3_VPC_ENDPOINT_URL
        )
        dest_s3_client = create_s3_client(
            DEST_AWS_ACCESS_KEY_ID,
            DEST_AWS_SECRET_ACCESS_KEY,
            DEST_AWS_REGION
        )
    except Exception:
        logger.error("Failed to initialize S3 clients. Exiting.")
        exit(1)

    # 2. Perform reconnaissance
    source_recon_ok = perform_source_recon(source_s3_client, SOURCE_BUCKET_NAME, SOURCE_OBJECT_KEY)
    dest_recon_ok = perform_destination_recon(dest_s3_client, DEST_BUCKET_NAME, DEST_OBJECT_KEY)

    if not source_recon_ok or not dest_recon_ok:
        logger.error("Reconnaissance failed. Please check configurations, credentials, and permissions. Exiting.")
        exit(1)
    else:
        logger.info("\nReconnaissance successful for both source and destination.")

    # 3. Execute the file transfer
    if transfer_s3_file(source_s3_client, dest_s3_client,
                        SOURCE_BUCKET_NAME, SOURCE_OBJECT_KEY,
                        DEST_BUCKET_NAME, DEST_OBJECT_KEY):
        logger.info("\nScript completed successfully!")
    else:
        logger.error("\nScript finished with errors. Please check logs for details.")


