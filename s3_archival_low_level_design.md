# S3 Archival 

## Low-Level Design (LLD)

### 1. Core Components

1. **DynamoDB Table: `S3ArchivalConfigurations`**
   - **Partition Key:** `JobGroupName` (String)
   - **Attributes:**
     - `JobGroupName` (String)
     - `ObjectType` (String) – Defines the file type category (e.g., "zip", "csv").
     - `Object` (String) – Represents object key pattern or a logical name/ID.
     - `Object_Reference` (String) – Additional reference ID for external integration.
     - `ExtractUnloadPath` (String) – S3 prefix/path where target objects reside (e.g., `s3://mybucket/path/`).
     - `ArchivalRuleReferenceAttributes` (Map/JSON) – Includes:
       - `ArchivalType` (String): One of `TagBased`, `COBDateBased`, `CreationTimeBased`.
       - `TagCriteria` (Map<String,String>): For TagBased rules.
       - `COBDatePattern` (String): Regex or date format to parse COB date from the filename.
       - `AllowedFileExtensions` (List<String>): E.g., [".zip",".csv"].
       - `UseInventory` (Boolean): Whether to use S3 Inventory for listing.
     - `StorageClass` (String) – e.g., "DEEP_ARCHIVE".
     - `NoOfDaysToArchival` (Number)
     - `SourceBucket` (String) – e.g., "my-source-bucket".
     - `TargetBucket` (String) – optional, only if direct move needed.
     - `Active` (Boolean) – Is the rule active?

2. **AWS Lambda Functions:**
   - `ConfigReaderLambda`: Fetches rules from DynamoDB.
   - `ArchivalProcessorLambda`: Processes each rule, identifies objects, and applies tags or moves them.
   - `IngestionTaggerLambda` (optional): Tags objects at upload based on file extension.
   - `InventoryProcessorLambda` (optional): Triggers upon new S3 Inventory reports, or invoked by the `ArchivalProcessorLambda` to read Inventory.

3. **S3 Inventory (Optional):**
   - A daily or weekly job that produces a manifest (CSV/Parquet) of all objects, including tags if enabled.
   - Inventory files stored in a known prefix (e.g., `s3://mybucket/inventory/`).

4. **EventBridge Schedule:**
   - Triggers `ConfigReaderLambda` daily (or as required).

---

### 2. Detailed Steps

#### 2.1 ConfigReaderLambda

**Trigger:** Scheduled via EventBridge (e.g., daily at midnight).

**Actions:**
1. Scan DynamoDB `S3ArchivalConfigurations` for `Active=true` items.
2. For each configuration (rule), send a message to an SQS queue or directly invoke `ArchivalProcessorLambda` asynchronously with payload:
   - `JobGroupName`
   - `ExtractUnloadPath`
   - `ArchivalType`
   - `AllowedFileExtensions`
   - `NoOfDaysToArchival`
   - `COBDatePattern` (if applicable)
   - `TagCriteria` (if applicable)
   - `UseInventory`
   - `SourceBucket`
   - `TargetBucket`
   - `StorageClass`

**Corner Cases:**
- If no active rules found, do nothing.
- Handle DynamoDB read throttling by pagination and exponential backoff.

---

#### 2.2 ArchivalProcessorLambda

**Trigger:** Invoked by `ConfigReaderLambda` or directly for testing.

**Parameters:** The configuration payload from above.

**High-Level Steps:**
1. Parse input configuration.
2. Based on `UseInventory`, choose listing approach:
   - If `UseInventory=true`, call `handleWithInventory()`.
   - Else, call `handleWithListObjects()`.

3. Filtering logic:
   - Retrieve list of candidate objects (from inventory or S3 listing).
   - Filter by `AllowedFileExtensions`.
   - Depending on `ArchivalType`, call the appropriate method:
     - `handleTagBasedArchival(objects, TagCriteria, NoOfDaysToArchival)`
     - `handleCOBDateBasedArchival(objects, COBDatePattern, NoOfDaysToArchival)`
     - `handleCreationTimeBasedArchival(objects, NoOfDaysToArchival)`

4. After filtering, you have a final list of objects eligible for archival.

5. Apply archival action:
   - If using lifecycle rules, apply a tag (e.g., `ArchiveEligible=true`) to each eligible object with `S3:PutObjectTagging`.
   - If direct move is needed (not recommended if lifecycle can handle it):
     - `copyObjectToTargetBucket()`
     - `deleteOriginalObject()`
   
6. Return success or log failures.

**Corner Cases:**
- If no objects match criteria, simply exit.
- Handle network failures with retries for tagging or copying.
- Ensure objects that are already archived or deleted are skipped.

---

#### 2.3 handleWithInventory()

**Purpose:** To use S3 Inventory for object listing.

**Steps:**
1. Identify the latest Inventory report file(s) for the `SourceBucket`.
2. Download (or read from S3 Select) the inventory manifest.
3. Parse the inventory CSV/Parquet to extract:
   - Object Key
   - Last Modified Date
   - Storage Class
   - Tags (if included)
4. Filter objects to only those in `ExtractUnloadPath` prefix.
5. Return the filtered list of objects for further archival checks.

**Corner Cases:**
- Inventory file not found or delayed: fallback to `handleWithListObjects()` or skip run.
- Missing tags in inventory: If tags are crucial and not included, you must do `GetObjectTagging` selectively.

---

#### 2.4 handleWithListObjects()

**Purpose:** Fallback if not using inventory or if inventory not available.

**Steps:**
1. Use `ListObjectsV2` with `Prefix=ExtractUnloadPath` to iterate over objects.
2. For each object:
   - Retrieve `LastModified` from object metadata.
   - If Tag-based archival: `GetObjectTagging` for each object.
3. Collect all objects in a list and return.

**Corner Cases:**
- For large buckets, pagination required with `ContinuationToken`.
- Watch out for API throttling and apply backoff.
- This approach may be slow and expensive for very large object sets.

---

#### 2.5 handleTagBasedArchival(objects, TagCriteria, NoOfDaysToArchival)

**Input:** A list of object metadata (including tags), `TagCriteria`, and `NoOfDaysToArchival`.

**Steps:**
1. For each object:
   - Check if object tags contain the required `TagCriteria` key-value pairs.
   - Check object age:
     - Age = CurrentDate - LastModifiedDate
     - If Age >= NoOfDaysToArchival and tags match criteria, mark object as eligible.
2. Return the filtered eligible objects.

**Corner Cases:**
- If `TagCriteria` is empty or null, skip tag check.
- If tags not found or object not tagged properly, skip object.

---

#### 2.6 handleCOBDateBasedArchival(objects, COBDatePattern, NoOfDaysToArchival)

**Input:** A list of objects, a COB date extraction pattern, and `NoOfDaysToArchival`.

**Steps:**
1. For each object key:
   - Parse the object key using `COBDatePattern`. E.g., regex to extract a substring representing COB date (e.g., YYYYMMDD).
   - Convert extracted substring to a Date object.
   - Age = CurrentDate - COBDate
   - If Age >= NoOfDaysToArchival, object is eligible.
2. Return eligible objects.

**Corner Cases:**
- If COBDate can’t be parsed (no match), skip object.
- If COBDate is malformed, consider object ineligible or log a warning.

---

#### 2.7 handleCreationTimeBasedArchival(objects, NoOfDaysToArchival)

**Input:** A list of objects and `NoOfDaysToArchival`.

**Steps:**
1. For each object:
   - Age = CurrentDate - LastModifiedDate
   - If Age >= NoOfDaysToArchival, object is eligible.
2. Return eligible objects.

**Corner Cases:**
- If `LastModifiedDate` is missing (unlikely), skip object.
- Large number of objects could require batching the results.

---

#### 2.8 Applying Lifecycle vs. Direct Move

**If Using Lifecycle:**
- For each eligible object:
  - `PutObjectTagging` with `{ "Key": "ArchiveEligible", "Value": "true" }` (example).
- Ensure an S3 Lifecycle rule is pre-configured:
  ```xml
  <Rule>
    <Filter>
      <Tag><Key>ArchiveEligible</Key><Value>true</Value></Tag>
    </Filter>
    <Status>Enabled</Status>
    <Transition>
      <Days>0</Days> <!-- or as per lifecycle design -->
      <StorageClass>DEEP_ARCHIVE</StorageClass>
    </Transition>
  </Rule>
  ```
  
**If Direct Move:**
- `copyObjectToTargetBucket(objectKey, SourceBucket, TargetBucket, StorageClass)`
- On success, `deleteObjectFromSourceBucket(objectKey, SourceBucket)`

**Corner Cases:**
- Ensure idempotency: If tagged or moved already, don’t duplicate actions.
- Handle partial failures in copy/delete with retries.

---

### 3. Error Handling and Logging

- Use structured logging to record:
  - Start/End of each Lambda
  - Number of objects processed, number eligible for archival
  - Any parsing or network errors
- Implement retries on S3 API operations (exponential backoff).
- If a COB date parsing fails repeatedly for a pattern, log an alert.

### 4. Performance and Scaling

- For large object sets:
  - Use Inventory reports to minimize API calls.
  - Consider S3 Batch Operations if direct moves are required for a very large set.
- Pagination and concurrency:
  - `ArchivalProcessorLambda` can process objects in batches.
  - If the list is huge, store state in DynamoDB or SQS and iterate in multiple runs.

### 5. Security and Access Control

- Grant Lambda roles `s3:GetObject`, `s3:PutObjectTagging`, `dynamodb:Scan`, `dynamodb:GetItem`, `dynamodb:Query`.
- If direct move, add `s3:PutObject` for `TargetBucket`.
- Enforce least privilege on IAM policies.

### 6. Corner Cases Summary

- Empty AllowedFileExtensions: Archive all files if no extensions restricted.
- No Active rules: No action.
- Inventory delayed: fallback or skip run.
- Tag-based rule but no tags: skip object.
- COBDate parsing fails: skip object, log warning.
- Direct move fails (network issue): retry, if still fails, log and proceed with next object.

---

## Conclusion

This Low-Level Design provides a concrete, step-by-step blueprint. It details how each archival type is handled, how objects are listed (via Inventory or direct ListObjects calls), how filtering and tagging are done, and how lifecycle or direct moves are applied. All corner cases, error handling, and scalability considerations are addressed to ensure the solution is robust, maintainable, and ready for implementation.
