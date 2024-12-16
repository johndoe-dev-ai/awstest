# S3 Archival Framework

## High-Level Design Overview

### Objective

The S3 Archival Framework aims to automatically archive S3 objects to a colder storage class (e.g., Glacier Deep Archive) after a certain retention period. It supports multiple archival strategies (Tag-based, COB date-based, Creation Time-based) and allows filtering by object type (e.g., `.zip` files). Archival configurations are stored in DynamoDB, enabling dynamic updates and centralized management. The framework can optionally leverage Amazon S3 Inventory reports for improved scalability, making it more efficient to handle large buckets with millions or billions of objects.

### Key Archival Approaches

1. **Tag-Based Archival:**  
   Identify objects based on specific tags once they reach a certain age.

2. **COB Date-Based Archival:**  
   Parse a COB (Close of Business) date embedded in filenames to determine the object’s age threshold.

3. **Creation Time-Based Archival:**  
   Archive objects older than a specified number of days based on their `LastModified` timestamp.

### Lifecycle or Direct Move Approach

- **Lifecycle-Rule-Based Archival:**  
  Tag objects according to the archival criteria. S3 Lifecycle rules defined on these tags or prefixes automatically transition objects after `NoOfDaysToArchival` to the desired `StorageClass`.

- **Direct Move Approach (Alternative):**  
  Use Lambda or Batch Operations to copy and then delete objects, if not relying on lifecycle transitions.

---

## DynamoDB Table Schema and Attributes

**Table Name:** `S3ArchivalConfigurations`

- **Partition Key:** `JobGroupName` (String)

**Attributes:**
1. **JobGroupName (String):** Logical grouping for the archival rule (e.g., a department, project, or workflow).
2. **ObjectType (String):** Specifies the type/category of objects this rule applies to (e.g., `zip` for `.zip` files).
3. **Object (String):** Identifier or pattern for target objects (e.g., an S3 prefix or file naming pattern).
4. **Object_Reference (String):** Additional reference or ID for tracking or integration with external systems.
5. **ExtractUnloadPath (String):** S3 prefix/path where target objects reside, guiding scanning or tagging operations.
6. **ArchivalRuleReferenceAttributes (Map/JSON):** Flexible field storing rule-specific details, for example:
   - **ArchivalType (String):** `TagBased`, `COBDateBased`, or `CreationTimeBased`
   - **TagCriteria (Map):** Key-value pairs for Tag-based rules
   - **COBDatePattern (String):** Regex or format to extract COB date from filenames
   - **AllowedFileExtensions (List):** Allowed file extensions (e.g., `[".zip", ".csv"]`)
7. **StorageClass (String):** Target storage class for archived objects (e.g., `DEEP_ARCHIVE`).
8. **NoOfDaysToArchival (Number):** Retention threshold in days.
9. **SourceBucket (String, optional):** Name of the S3 bucket containing the source objects.
10. **TargetBucket (String, optional):** Name of the target bucket if objects must be moved (optional if using lifecycle rules in the same bucket).
11. **Active (Boolean, optional):** Whether the rule is currently active.

---

## Process Flow

1. **Configuration Retrieval:**  
   A Lambda function (triggered by EventBridge) periodically reads the DynamoDB table for active `JobGroupName` rules.

2. **Object Identification:**
   Based on `ArchivalType` and `AllowedFileExtensions`, the function identifies objects due for archival.
   
   - **Tag-Based:** Identify objects with matching tags and older than `NoOfDaysToArchival`.
   - **COB Date-Based:** Parse the object key using `COBDatePattern` to determine its age.
   - **Creation Time-Based:** Compare `LastModified` date with the retention threshold.

3. **File Type Filtering:**  
   Filter objects by `ObjectType` and `AllowedFileExtensions` before archival actions.

4. **Tagging or Archival Action:**
   - If using lifecycle rules: Tag eligible objects (e.g., `ArchiveEligible=true`) so that pre-configured lifecycle policies transition them after the specified time.
   - If using a direct move: Copy objects to `TargetBucket` or change storage class and remove them from the source.

---

## Optional: Using S3 Inventory for Scalability

**What is S3 Inventory?**  
Amazon S3 Inventory provides a daily or weekly list of all objects in an S3 bucket or prefix. Each report is a CSV or Parquet file stored in a specified S3 location, containing metadata such as:
- Object key
- Last modified date
- Storage class
- Object size
- Object tags (if requested)

**How S3 Inventory Helps:**
- **Efficient Object Discovery at Scale:**  
  Instead of using `ListObjectsV2` calls repeatedly (which may be slow and expensive for large buckets), the framework can process the inventory files to quickly get a list of all objects.
  
- **Filtering by Extension or Tag:**  
  By including tags in the S3 Inventory configuration, the Lambda function can filter objects locally by reading from the inventory file, rather than making multiple `GetObjectTagging` calls.
  
- **Batch Processing:**  
  Using S3 Inventory, the Lambda (or AWS Glue/Athena) can query the inventory reports to find objects older than `NoOfDaysToArchival`, with a matching prefix, extension, or tag.

**S3 Inventory Setup:**
1. **Enable S3 Inventory on Source Bucket:**  
   - Configure daily or weekly frequency.
   - Include required metadata fields (Last Modified, Storage Class).
   - Consider including `Object Tags` in the inventory.
   
2. **Processing Inventory Reports:**  
   - A separate Lambda (triggered after the inventory file is delivered) or a scheduled Lambda reads the latest inventory report.
   - The Lambda filters objects based on the criteria stored in DynamoDB (`ArchivalType`, `AllowedFileExtensions`, `NoOfDaysToArchival`).
   - Eligible objects are either:
     - Tagged for lifecycle transitions.
     - Processed by S3 Batch Operations for direct archival moves.

**Integration with DynamoDB Config:**
- The DynamoDB entry can contain a flag (e.g., `UseInventory=true`) that indicates the framework should use the S3 Inventory reports instead of listing objects through API calls.
- The `ExtractUnloadPath` might point to the inventory output location or a prefix inside the source bucket that inventory covers.

**Lifecycle Example Using Inventory:**
1. Inventory report is generated daily.
2. Lambda reads DynamoDB config, sees that `UseInventory=true` and `ArchivalType=CreationTimeBased`, `ObjectType=zip`, `AllowedFileExtensions=[".zip"]`.
3. The Lambda queries/filters the inventory file for `.zip` objects older than `NoOfDaysToArchival`.
4. Lambda tags these objects with `FileType=zip` and `ArchiveEligible=true`.
5. S3 Lifecycle rule transitions tagged objects to `DEEP_ARCHIVE` after the specified period.

---

## Limitations

1. **Lifecycle Rule Limit:**  
   A maximum of 1,000 lifecycle rules per bucket. Partitioning or careful design may be required for large scale.

2. **File Extension Filtering:**  
   S3 Lifecycle rules do not natively filter by extension. Tagging or using prefixes is necessary.

3. **Tag Retrieval Cost (if not using Inventory):**  
   Without inventory, multiple `GetObjectTagging` calls can be expensive. Inventory reduces this cost by providing a bulk snapshot of tags.

4. **Inventory Latency:**
   Inventory is generated daily or weekly (not real-time), so archival decisions may not be immediate. There is a delay between object creation and the inventory availability.

---

## Summary

In this enhanced design, the DynamoDB configuration table defines archival rules, including object type, archival type, allowed extensions, and retention periods. By optionally leveraging S3 Inventory, the framework can efficiently handle large-scale operations. The inventory reduces the need for time-consuming listing and tagging calls, enabling the Lambda functions to identify eligible objects through a bulk dataset. Once identified, objects are either tagged for lifecycle-based archival or moved directly, fulfilling all requirements for flexible, scalable, and cost-efficient S3 archival.
