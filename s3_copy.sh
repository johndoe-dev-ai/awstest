#!/bin/bash

# --- Configuration ---
# IMPORTANT: For production, avoid hardcoding credentials.
# Use environment variables, AWS Secrets Manager, or IAM roles for EC2 instances.

# Source S3 Bucket Configuration
SOURCE_AWS_ACCESS_KEY_ID="YOUR_SOURCE_AWS_ACCESS_KEY_ID"
SOURCE_AWS_SECRET_ACCESS_KEY="YOUR_SOURCE_AWS_SECRET_ACCESS_KEY"
SOURCE_AWS_REGION="YOUR_SOURCE_AWS_REGION"
SOURCE_BUCKET_NAME="your-source-bucket-name"
SOURCE_OBJECT_KEY="path/to/your/large_file.zip"
# If using a VPC Endpoint, provide its URL here.
# Example: "vpce-0123456789abcdef0-abcdefg.s3.your-source-aws-region.vpce.amazonaws.com"
# If not using a VPC endpoint, set to an empty string.
SOURCE_S3_VPC_ENDPOINT_URL="" # "YOUR_S3_VPC_ENDPOINT_URL_HERE"


# Destination S3 Bucket Configuration
DEST_AWS_ACCESS_KEY_ID="YOUR_DEST_AWS_ACCESS_KEY_ID"
DEST_AWS_SECRET_ACCESS_KEY="YOUR_DEST_AWS_SECRET_ACCESS_KEY"
DEST_AWS_REGION="YOUR_DEST_AWS_REGION"
DEST_BUCKET_NAME="your-destination-bucket-name"
DEST_OBJECT_KEY="path/to/new_large_file.zip" # Can be same as SOURCE_OBJECT_KEY

# --- Script Setup ---
set -e # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Exit if any command in a pipeline fails.

# Use a temporary file for download/upload, ensuring it's unique
TEMP_FILE_PATH=$(mktemp /tmp/s3_transfer_XXXXXX.tmp)

# Ensure the temporary file is cleaned up on exit (even if script fails)
trap "rm -f \"$TEMP_FILE_PATH\"" EXIT

echo "--- Starting S3 File Transfer Script (AWS CLI) ---"
echo "Temporary file created at: $TEMP_FILE_PATH"

# --- Functions for Reconnaissance ---

perform_source_recon() {
    local bucket_name="$1"
    local object_key="$2"
    local region="$3"
    local endpoint_url="$4"

    echo -e "\n--- Source S3 Reconnaissance for '$bucket_name/$object_key' ---"

    # Set source credentials for this step
    export AWS_ACCESS_KEY_ID="$SOURCE_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$SOURCE_AWS_SECRET_ACCESS_KEY"
    export AWS_DEFAULT_REGION="$region"

    # Check bucket existence and permissions
    if [ -n "$endpoint_url" ]; then
        aws s3api head-bucket --bucket "$bucket_name" --endpoint-url "$endpoint_url" &> /dev/null
    else
        aws s3api head-bucket --bucket "$bucket_name" &> /dev/null
    fi

    if [ $? -ne 0 ]; then
        echo "Error: Source bucket '$bucket_name' not found or access denied." >&2
        return 1
    fi
    echo "Source bucket '$bucket_name' exists."

    # Check object existence and get metadata
    local head_object_cmd
    if [ -n "$endpoint_url" ]; then
        head_object_cmd="aws s3api head-object --bucket \"$bucket_name\" --key \"$object_key\" --endpoint-url \"$endpoint_url\""
    else
        head_object_cmd="aws s3api head-object --bucket \"$bucket_name\" --key \"$object_key\""
    fi

    OBJECT_METADATA=$($head_object_cmd 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Source object '$object_key' not found in bucket '$bucket_name' or access denied." >&2
        return 1
    fi

    FILE_SIZE=$(echo "$OBJECT_METADATA" | grep ContentLength | awk '{print $2}' | tr -d ',')
    LAST_MODIFIED=$(echo "$OBJECT_METADATA" | grep LastModified | cut -d ':' -f2- | tr -d '",')

    echo "Source object '$object_key' found."
    echo "  Size: $FILE_SIZE bytes"
    echo "  Last Modified: $LAST_MODIFIED"
    return 0
}

perform_destination_recon() {
    local bucket_name="$1"
    local region="$2"

    echo -e "\n--- Destination S3 Reconnaissance for '$bucket_name' ---"

    # Set destination credentials for this step
    export AWS_ACCESS_KEY_ID="$DEST_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$DEST_AWS_SECRET_ACCESS_KEY"
    export AWS_DEFAULT_REGION="$region"

    # Check bucket existence and permissions
    aws s3api head-bucket --bucket "$bucket_name" &> /dev/null
    if [ $? -ne 0 ]; then
        echo "Error: Destination bucket '$bucket_name' not found or access denied." >&2
        return 1
    fi
    echo "Destination bucket '$bucket_name' exists."

    # Optional: Test write permissions by attempting to put a tiny object and delete it
    local test_key="recon_test_permissions_$(date +%s%N)"
    echo -n "" | aws s3 cp - "s3://$bucket_name/$test_key" --expected-bucket-owner "$DEST_AWS_ACCESS_KEY_ID" &> /dev/null
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to confirm write permissions for destination bucket '$bucket_name'. Proceeding but be aware." >&2
    else
        echo "Write permissions confirmed for destination bucket '$bucket_name'."
        aws s3 rm "s3://$bucket_name/$test_key" &> /dev/null # Clean up test object
    fi

    return 0
}


# --- Main Execution ---

# 1. Perform reconnaissance
echo "Performing reconnaissance..."
if ! perform_source_recon "$SOURCE_BUCKET_NAME" "$SOURCE_OBJECT_KEY" "$SOURCE_AWS_REGION" "$SOURCE_S3_VPC_ENDPOINT_URL"; then
    echo "Reconnaissance for source failed. Exiting." >&2
    exit 1
fi

if ! perform_destination_recon "$DEST_BUCKET_NAME" "$DEST_AWS_REGION"; then
    echo "Reconnaissance for destination failed. Exiting." >&2
    exit 1
fi

echo -e "\nReconnaissance successful for both source and destination."

# 2. Download the file from source S3
echo -e "\n--- Starting Download from Source S3 ---"
echo "Source: s3://$SOURCE_BUCKET_NAME/$SOURCE_OBJECT_KEY"
echo "Downloading to: $TEMP_FILE_PATH"

# Set source credentials for download
export AWS_ACCESS_KEY_ID="$SOURCE_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$SOURCE_AWS_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="$SOURCE_AWS_REGION"

if [ -n "$SOURCE_S3_VPC_ENDPOINT_URL" ]; then
    echo "Using VPC endpoint URL: $SOURCE_S3_VPC_ENDPOINT_URL"
    aws s3 cp "s3://$SOURCE_BUCKET_NAME/$SOURCE_OBJECT_KEY" "$TEMP_FILE_PATH" --endpoint-url "$SOURCE_S3_VPC_ENDPOINT_URL"
else
    aws s3 cp "s3://$SOURCE_BUCKET_NAME/$SOURCE_OBJECT_KEY" "$TEMP_FILE_PATH"
fi

echo "Download complete: $(du -h "$TEMP_FILE_PATH" | awk '{print $1}') downloaded."


# 3. Upload the file to destination S3
echo -e "\n--- Starting Upload to Destination S3 ---"
echo "Uploading from: $TEMP_FILE_PATH"
echo "Destination: s3://$DEST_BUCKET_NAME/$DEST_OBJECT_KEY"

# Set destination credentials for upload
export AWS_ACCESS_KEY_ID="$DEST_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$DEST_AWS_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="$DEST_AWS_REGION"

aws s3 cp "$TEMP_FILE_PATH" "s3://$DEST_BUCKET_NAME/$DEST_OBJECT_KEY"

echo "Upload complete."

echo -e "\n--- S3 File Transfer Script Completed Successfully! ---"

