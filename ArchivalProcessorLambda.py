import json
import boto3
import re
import csv
import io
from datetime import datetime, timezone, timedelta

s3 = boto3.client('s3')

# Constants for inventory (Adjust these to your actual inventory location)
INVENTORY_BUCKET = "my-inventory-bucket"    # The bucket where inventory files are stored
INVENTORY_KEY = "inventory/report.csv"      # The full key (path) to a single inventory CSV
# Inventory CSV expected columns: Example: "Bucket, Key, LastModifiedDate, ETag, Size, StorageClass, ..."

def lambda_handler(event, context):
    """
    This Lambda expects a single archival rule as input.
    'event' is a dictionary representing one item from DynamoDB returned by ConfigReaderLambda.

    The code will:
    - Determine archival method and approach (Tag-based, COB-date-based, Creation-time-based).
    - Use either inventory or direct listing to find candidate objects.
    - Filter objects by allowed extensions and age criteria.
    - Tag eligible objects for lifecycle archival.
    """
    
    # Extract configuration
    job_group_name = event.get("JobGroupName")
    archival_attrs = event.get("ArchivalRuleReferenceAttributes", {})
    archival_type = archival_attrs.get("ArchivalType")
    allowed_extensions = archival_attrs.get("AllowedFileExtensions", [])
    cob_date_pattern = archival_attrs.get("COBDatePattern", None)
    tag_criteria = archival_attrs.get("TagCriteria", {})
    use_inventory = archival_attrs.get("UseInventory", False)
    
    extract_unload_path = event.get("ExtractUnloadPath")
    no_of_days = event.get("NoOfDaysToArchival")
    source_bucket = event.get("SourceBucket")
    target_bucket = event.get("TargetBucket")  # Not used in this example (we rely on lifecycle tagging)
    storage_class = event.get("StorageClass")  # Not used directly here, but lifecycle rules will use it.

    if not (archival_type and no_of_days and source_bucket and extract_unload_path is not None):
        return {
            "status": "error",
            "message": "Missing required configuration attributes.",
            "jobGroupName": job_group_name
        }

    # Determine object listing approach
    if use_inventory:
        objects = handleWithInventory(source_bucket, extract_unload_path)
    else:
        objects = handleWithListObjects(source_bucket, extract_unload_path)

    # Filter by allowed file extensions if provided
    if allowed_extensions:
        objects = [o for o in objects if any(o['Key'].endswith(ext) for ext in allowed_extensions)]
    
    # Apply archival logic based on archival_type
    if archival_type == "TagBased":
        eligible_objects = handle_tag_based_archival(objects, tag_criteria, no_of_days, source_bucket)
    elif archival_type == "COBDateBased":
        if not cob_date_pattern:
            return {
                "status": "error",
                "message": "COBDateBased archival requires COBDatePattern.",
                "jobGroupName": job_group_name
            }
        eligible_objects = handle_cob_date_based_archival(objects, cob_date_pattern, no_of_days)
    elif archival_type == "CreationTimeBased":
        eligible_objects = handle_creation_time_based_archival(objects, no_of_days)
    else:
        return {
            "status": "error",
            "message": f"Unknown ArchivalType: {archival_type}",
            "jobGroupName": job_group_name
        }

    # Tag eligible objects for lifecycle rule
    tag_key = "ArchiveEligible"
    tag_value = "true"
    tagged_count = 0

    for obj in eligible_objects:
        try:
            s3.put_object_tagging(
                Bucket=source_bucket,
                Key=obj['Key'],
                Tagging=f"<Tagging><Tag><Key>{tag_key}</Key><Value>{tag_value}</Value></Tag></Tagging>"
            )
            tagged_count += 1
        except Exception as e:
            # Log error and continue
            print(f"Failed to tag {obj['Key']}: {str(e)}")

    return {
        "status": "success",
        "jobGroupName": job_group_name,
        "archivalType": archival_type,
        "taggedObjectsCount": tagged_count
    }

def handleWithInventory(source_bucket, prefix):
    """
    Reads a CSV inventory file from a known S3 location.
    Filters objects by the given prefix.
    Expects CSV format with columns at least: Bucket,Key,LastModifiedDate,StorageClass
    Adjust parsing as per your actual inventory schema.
    """
    response = s3.get_object(Bucket=INVENTORY_BUCKET, Key=INVENTORY_KEY)
    body = response['Body'].read().decode('utf-8')
    reader = csv.reader(io.StringIO(body))
    
    # Assuming first line is header
    headers = next(reader)
    # Identify required column indices
    # Typical headers could be: Bucket, Key, LastModifiedDate, ETag, Size, StorageClass ...
    # We need at least Bucket, Key, LastModifiedDate
    try:
        bucket_idx = headers.index("Bucket")
        key_idx = headers.index("Key")
        last_mod_idx = headers.index("LastModifiedDate")
    except ValueError as e:
        # Columns not found, raise an error
        raise RuntimeError("Required columns not found in inventory file")

    objects = []
    for row in reader:
        obj_bucket = row[bucket_idx]
        obj_key = row[key_idx]
        obj_last_modified_str = row[last_mod_idx]

        if obj_bucket == source_bucket and obj_key.startswith(prefix):
            # Parse last modified date
            # Inventory date format is typically ISO8601: e.g. 2021-07-25T03:45:00Z
            last_modified = datetime.strptime(obj_last_modified_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            objects.append({
                "Key": obj_key,
                "LastModified": last_modified
            })
    return objects

def handleWithListObjects(bucket, prefix):
    """
    Lists objects from the bucket using ListObjectsV2. Handles pagination.
    Returns a list of objects with 'Key' and 'LastModified'.
    """
    objects = []
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get('Contents', []):
            objects.append({
                "Key": item['Key'],
                "LastModified": item['LastModified'] if 'LastModified' in item else None
            })
    return objects

def handle_tag_based_archival(objects, tag_criteria, no_of_days, bucket):
    """
    For each object, ensure it has required tags and is older than no_of_days.
    Returns only the eligible objects.
    """
    if not tag_criteria:
        # If no criteria, then just age-check
        needed_tags = {}
    else:
        needed_tags = tag_criteria  # key-value pairs

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=no_of_days)
    eligible = []
    for obj in objects:
        # Age check
        if obj['LastModified'] and obj['LastModified'] < cutoff_date:
            # Check tags if any
            if needed_tags:
                object_tags = get_object_tags(bucket, obj['Key'])
                # Check if all needed tags are present and match
                if all(object_tags.get(k) == v for k,v in needed_tags.items()):
                    eligible.append(obj)
            else:
                # No tag criteria, just age
                eligible.append(obj)
    return eligible

def handle_cob_date_based_archival(objects, cob_date_pattern, no_of_days):
    """
    Parse COB date from filename using cob_date_pattern regex.
    Format assumed YYYYMMDD or similar. Adjust regex & parsing as needed.
    Compare COB date + no_of_days with current date.
    """
    cutoff_date = datetime.now(timezone.utc)
    # We'll assume cob_date_pattern is a regex with a group that extracts date like YYYYMMDD
    # Example regex: r".*(\d{8}).*"
    regex = re.compile(cob_date_pattern)
    eligible = []
    for obj in objects:
        m = regex.match(obj['Key'])
        if m:
            date_str = m.group(1)
            try:
                # Parse date_str as YYYYMMDD
                cob_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
                # If COB date + no_of_days <= now, eligible
                if cob_date + timedelta(days=no_of_days) <= cutoff_date:
                    eligible.append(obj)
            except ValueError:
                # If parsing fails, skip
                continue
    return eligible

def handle_creation_time_based_archival(objects, no_of_days):
    """
    Check if object's LastModified is older than no_of_days.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=no_of_days)
    eligible = [obj for obj in objects if obj['LastModified'] and obj['LastModified'] < cutoff_date]
    return eligible

def get_object_tags(bucket, key):
    """
    Returns a dictionary of object tags {TagKey: TagValue} for the specified S3 object.
    """
    try:
        tag_resp = s3.get_object_tagging(Bucket=bucket, Key=key)
        tags = {t['Key']: t['Value'] for t in tag_resp.get('TagSet', [])}
        return tags
    except s3.exceptions.NoSuchKey:
        return {}
    except Exception as e:
        # If error retrieving tags, return empty. 
        # Might decide differently, but we'll skip object if tags cannot be fetched.
        print(f"Error getting tags for {key}: {str(e)}")
        return {}
