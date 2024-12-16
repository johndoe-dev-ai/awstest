# S3 Archival Policy

## Overview

The archival framework’s main goal is to move eligible objects from a "hot" storage tier (S3 Standard or similar) to a "cold" storage tier (Glacier Deep Archive) after a certain period. Previously, the approach relied heavily on Lambda and DynamoDB for decision-making and object-by-object moves. By adopting a lifecycle-rule-based approach, we can leverage Amazon S3’s built-in lifecycle management for simpler, more cost-effective, and automated archival. 

However, S3 Lifecycle rules cannot directly filter by file extensions. They filter by prefix, object tags, or object age. To accommodate file-type-specific archival (e.g., `.zip` files only), we must define a strategy at ingestion or post-ingestion tagging. For instance, we can:

- Use object tags to mark files that qualify for a particular archival policy.
- Organize files into dedicated prefixes or folders that represent the file type and meet certain selection criteria.

---

## Key Requirements

1. **Archival Types:**
   - **Tag-based Archival:** Identify objects by specific object tags.
   - **COB Date-Based Archival:** Identify objects based on a COB (Close of Business) date embedded in the filename. After processing, tag them accordingly.
   - **Creation Time-Based Archival:** Identify objects older than a specified number of days. Once identified, tag these objects.

2. **Configuration Storage:**
   - A DynamoDB table to store the archival configurations, including:
     - **Archival Type** (Tag-Based, COB Date-Based, Creation Time-Based)
     - **Days Threshold** (Number of days after which objects should be archived)
     - **Allowed File Types** (e.g., `.zip` only, or `.csv`, `.parquet`, etc.)
     - **Tag Keys/Values** (For tag-based approach)
     - **COB Date Pattern** (For parsing date from filenames)
     - **Prefixes or Tagging Strategies** for applying lifecycle rules.

3. **Lifecycle Rule Integration:**
   - Instead of performing object-by-object moves through Lambda, the framework will apply object tags or place objects in dedicated prefixes that have corresponding lifecycle rules to transition objects to Glacier Deep Archive after the defined threshold.

4. **Handling `.zip` Files:**
   - S3 Lifecycle rules do not support direct filtering by file extension.
   - To address this, one approach is:
     1. **Tagging `.zip` Files at Ingestion:** When `.zip` files are uploaded, a trigger (e.g., S3 Event + Lambda) can inspect the filename, and if it matches `.zip`, it applies a tag like `FileType=zip`.
     2. **Lifecycle Rule on Tag:** Create a lifecycle configuration that says:  
        *If `FileType=zip` and object age > X days, transition to Glacier Deep Archive.*  
     - Alternatively, if the bucket structure is well-organized, `.zip` files could be placed in a prefix like `zip/`. Then a lifecycle rule can be configured to apply to all objects under `zip/`.

---

## High-Level Architecture

### Components

1. **Source S3 Bucket:**  
   All incoming files are placed here. The bucket may have multiple prefixes, or an ingestion Lambda that tags objects based on their file type and other criteria.

2. **DynamoDB Configuration Table (S3ArchivalConfigurations):**
   - **Partition Key:** `JobGroupName_ArchivalType`
   - **Attributes:**
     - `ArchivalType` (e.g. `TagBased`, `COBDateBased`, `CreationTimeBased`)
     - `DaysThreshold` (Number)
     - `AllowedFileTypes` (List, e.g., `[".zip"]`)
     - `SourceBucket` (String)
     - `LifecycleTagKey` and `LifecycleTagValue` (e.g., `FileType=zip`)
     - `COBDatePattern` (if required)
     - `Active` (Boolean)

3. **Lambda Functions & Event Flows:**
   - **Configuration Reader Lambda (Triggered by EventBridge):**  
     - Periodically queries DynamoDB to retrieve active configurations.
     - For COB date-based or creation-time-based archival:
       - Identifies objects that meet the criteria (using S3 Inventory or ListObjects).
       - Applies the necessary tags (e.g., `FileType=zip` or `ArchiveEligible=true`) to these objects if they match the criteria.
   
   - **Ingestion/Tagging Lambda (S3 Event Triggered):**  
     - On object upload, checks the file extension.
     - If it matches `.zip` (or any allowed type), assigns the correct tag (e.g., `FileType=zip`).  
     This ensures objects are correctly classified from the start.
   
4. **S3 Lifecycle Configuration:**
   - A lifecycle rule in the source bucket (or archive bucket if moving between buckets) that:
     - Filters objects by tag: `FileType=zip` or `ArchiveEligible=true`.
     - After `DaysThreshold` days from object creation, transitions them to Glacier Deep Archive.
   - One or multiple lifecycle rules can be defined based on different tag sets (e.g., one for `.zip`, one for `.csv`, etc.).

### Data Flow

1. **Ingestion Phase (for `.zip` example):**
   - A `.zip` file is uploaded to `s3://source-bucket/`.
   - S3 triggers the Ingestion Lambda.
   - Ingestion Lambda checks the file extension; if `.zip`, it applies the tag `FileType=zip` to the object.
   - The object now is "pre-classified" for the lifecycle rule that is set to archive `.zip` files after `X` days.

2. **COB Date / Creation Time-Based:**
   - For configurations defined in DynamoDB, the Configuration Reader Lambda runs periodically (e.g., daily).
   - It fetches all objects from the bucket using S3 Inventory or filtered ListObjects calls.
   - If an object is older than the `DaysThreshold` or matches COB date criteria and is of the correct file type, the Configuration Reader Lambda applies a tag (e.g., `ArchiveEligible=true`).
   - A lifecycle rule set to look for `ArchiveEligible=true` objects will eventually transition them after the configured timeframe.

3. **Lifecycle Transition:**
   - S3 Lifecycle rule checks object tags and age.
   - When conditions are met, it transitions objects to Glacier Deep Archive automatically.

### Example Lifecycle Rule Configuration (Pseudocode)

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>ArchiveZipFiles</ID>
    <Filter>
      <Tag>
        <Key>FileType</Key>
        <Value>zip</Value>
      </Tag>
    </Filter>
    <Status>Enabled</Status>
    <Transition>
      <Days>30</Days>
      <StorageClass>GLACIER_DEEP_ARCHIVE</StorageClass>
    </Transition>
  </Rule>
</LifecycleConfiguration>
```

If a `.zip` file is uploaded and tagged with `FileType=zip` at ingestion, this rule moves it to Glacier Deep Archive 30 days later.

---

## Limitations and Considerations

1. **File Extension Filtering:**
   - Lifecycle rules cannot directly filter by extension. The ingestion Lambda or a post-processing Lambda must tag objects based on their extension.

2. **Scalability:**
   - Applying tags at ingestion scales well if objects are consistently uploaded and the tagging Lambda can handle the throughput.  
   - For COB or creation-time-based archival, a periodic process is needed to tag older objects. This might require scanning large numbers of objects and applying tags, which could lead to additional costs and overhead.

3. **Tag and Prefix Limitations:**
   - Each lifecycle rule can filter on a prefix or a single set of tags. Complex filtering might require multiple rules or pre-processing steps.
   
4. **Number of Rules:**
   - A single bucket can have up to 1,000 lifecycle rules. If the solution requires a very large number of discrete rules (e.g., different prefixes or different tags for numerous file types), you might approach this limit.
   
5. **File Types:**
   - If multiple file extensions need different archival times, you may need multiple sets of lifecycle rules or multiple tagging strategies.
   - Keep the number of distinct file types and associated tags manageable to avoid complexity.

6. **Backfilling Older Data:**
   - For existing older objects, a one-time tagging job (using S3 Batch Operations or a scanning Lambda) might be needed to ensure those objects have the appropriate tags so they can be picked up by the lifecycle rules.

---

## Conclusion

By leveraging S3 Lifecycle rules, the archival framework simplifies the actual data movement to Glacier Deep Archive. The DynamoDB table stores configurations and guides tagging strategies. The Lambda functions handle tagging based on extension, COB date, or creation time criteria. Through tagging, lifecycle rules know which objects to archive, ensuring a streamlined and largely automated archival process. This approach meets the requirement to handle `.zip` files (and other extensions) by integrating a tagging step and corresponding lifecycle filters.
