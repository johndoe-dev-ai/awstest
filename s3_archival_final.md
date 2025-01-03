### S3 Archival Solution

---

### Day 0 Approach (Immediate Transition for Zipped Files)
- **Description**  
  Create an Amazon S3 Lifecycle rule for each relevant prefix (for example, `abc/def/`) to transition `.zip` files to the **S3 DEEP_ARCHIVE** storage class if they are older than one month.  

- **Implementation Notes**  
  1. Configure a lifecycle rule in the Amazon S3 console or via IaC (e.g., AWS CloudFormation, Terraform).  
  2. For each prefix, set the filter to match files with the `.zip` extension and choose the DEEP_ARCHIVE transition for objects older than 30 days.  

- **Pros**  
  - Quick to implement for immediate or “Day 0” archiving requirements.  
  - No additional AWS services or complex setups required.  
  
- **Limitations**  
  - No option to filter by suffix in S3 Lifecycle rules; filtering is limited to prefix-based criteria.  
  - Not flexible for more complex filtering (e.g., requiring a combination of prefix + substring + custom tagging).  
  - Lifecycle transitions are bucket-wide; changes to selection criteria require updating or creating new lifecycle rules.  

---

### [Placeholder for Image 1: Illustrating Day 0 Lifecycle Rule Configuration]

*(Masking any sensitive path or bucket names.)*

---

### Alternative for Day 0 Approach (Using S3 Batch Operations for Zip Tagging)
- **Description**  
  Instead of a straight lifecycle rule, set up an **S3 Batch Operations** job to tag `.zip` files older than a specified number of days. Then use a lifecycle rule that transitions only objects tagged with `ArchiveEligible=True` to DEEP_ARCHIVE.

- **Key Steps**  
  1. **S3 Batch Operations** job uses a manifest (automatically generated or custom).  
  2. The job applies a tag (e.g., `ArchiveEligible=True`) to all `.zip` or `.zip.done` objects older than the threshold.  
  3. A lifecycle rule transitions any object with `ArchiveEligible=True` to DEEP_ARCHIVE.

- **Pros**  
  - Offers more control over which objects get transitioned.  
  - Tag-based transitions make it straightforward to see which items are archived.  
  - Allows combining prefix and substring-based filtering.

- **Limitations**  
  - Requires setup of an S3 Batch job and a suitable manifest (S3 Inventory or custom).  
  - Slightly more complex than a direct lifecycle rule.

---

### [Placeholder for Image 2: Illustrating S3 Batch Operations Tagging Flow]

*(Masking any sensitive path or bucket names.)*

---

### BAU (Business-As-Usual) Approaches

#### Approach 1: S3 Batch Operation Job Using S3 Inventory Report’s Manifest

1. **Generate S3 Inventory**  
   - Configure S3 Inventory for a bucket or a specific prefix (e.g., `abc/def/`).  
   - S3 Inventory runs on a weekly basis (frequency can vary).

2. **Identify Objects to Archive**  
   - The inventory report (in CSV or ORC/Parquet format) lists all objects and metadata (like last modified date).  
   - A separate configuration or a DynamoDB table can track how many days old the objects must be before archiving.

3. **Create S3 Batch Operations Job**  
   - Use the inventory report as the manifest input to the Batch job.  
   - The Batch job tags the required objects with `ArchiveEligible=True`.

4. **Apply Lifecycle Rule**  
   - A lifecycle rule (for the prefix in question) automatically transitions all objects tagged with `ArchiveEligible=True` to DEEP_ARCHIVE.

**Pros**  
- Re-uses S3 Inventory (a built-in Amazon S3 feature).  
- Scalable for large data sets.  
- Filters/conditions can be updated offline before creating the Batch job.

**Limitations**  
1. The manifest file **must** be encrypted with SSE-S3 (as required by S3 Batch Operations).  
2. The IAM role creating the job needs sufficient permissions to read the manifest and apply tags.  
3. The manifest CSV file cannot have a header row.  

---

### [Placeholder for Image 3: Screenshot of Approach 1 with Masked Bucket/Prefix Details]

---

#### Approach 2: S3 Batch Operation Job Using `S3JobManifestGenerator`
1. **Define Criteria (Prefix, Suffix, or Substring)**  
   - A DynamoDB table might store which prefix, suffix, or substring qualifies objects for archive or restore.  
   - Example: `prefix = abc/…`, `substring = 20200929`.

2. **Create Manifest Programmatically**  
   - Use the AWS SDK or custom code to call [`S3JobManifestGenerator`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_S3JobManifestGenerator.html).  
   - This automatically creates a manifest file containing only the objects that match your criteria.

3. **Run S3 Batch Operation**  
   - After the manifest is generated, an S3 Batch Operations job can apply tags or directly initiate restore/transition operations on the selected objects.

**Pros**  
- Eliminates the need for manually managing or storing an S3 Inventory manifest.  
- Highly customizable with programmatic control over the selection process.

**Limitations**  
- More moving parts: additional code to generate the manifest, store it, and invoke the Batch job.  
- Requires careful IAM permissions and security checks for the generation process and the subsequent job.

---

### [Placeholder for Image 4: Screenshot Illustrating Approach 2 Manifest Creation Flow]

---

### Automated Retrieval Framework

For restoring objects from DEEP_ARCHIVE back to a usable storage class, a similar approach can be used:

1. **DynamoDB Table for Restore Requests**  
   - Fields might include `jobGroupName`, `prefix`, `suffix`, or `substring` indicating which objects need to be restored.

2. **Lambda Function Trigger**  
   - Monitors the table for any new restore requests.  
   - Uses the stored criteria to generate a new S3 Batch Operations manifest (with `S3JobManifestGenerator`) for the archived objects.

3. **Initiate Restore Operation**  
   - Calls the [`S3InitiateRestoreObject`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_S3InitiateRestoreObjectOperation.html) via the S3 Batch Operations **create job** API.  
   - All objects mentioned in the manifest file will be restored from DEEP_ARCHIVE.

---

### [Placeholder for Image 5: Diagram of Automated Retrieval Framework]

---

## Flow Diagram (Example)

Below is a generic flow to illustrate how objects move into DEEP_ARCHIVE and can later be restored. (Adjust as needed.)

```
┌───────────────────┐
│  S3 Bucket         │
└─────────┬─────────┘
          │
          ▼
    [Check Age / Tag]
          │
          ▼
  ┌────────────────────┐
  │ Lifecycle Rule OR   │
  │ S3 Batch Operation  │
  └────────────────────┘
          │
          ▼
   Objects moved to
     DEEP_ARCHIVE
          │
          ▼
 [On Restore Request]
  ┌────────────────────┐
  │  Dynamodb + Lambda │
  │  + Batch Operation │
  └────────────────────┘
          │
          ▼
   Objects restored
```

---

## Masked Information
In any screenshots or logs you include, please ensure that:
- Specific bucket names, account IDs, and user names are replaced with placeholders (e.g., `******`).  
- Any proprietary prefixes or file paths are sanitized or anonymized.

---

### References
- [S3 Batch Operations Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-create-job.html)  
- [Troubleshooting S3 Batch Operations](https://aws.amazon.com/premiumsupport/knowledge-center/s3-troubleshoot-batch-operations/)  
- [API Control for S3 Batch Operations](https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_S3JobOperation.html)  
- [S3 Manifest Generator API Documentation](https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_S3JobManifestGenerator.html)  
- [S3 Initiate Restore Object Operation](https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_S3InitiateRestoreObjectOperation.html)

---

_End of Document_

