Requirement Document: S3 Zip File Archival Framework
Objective
To design and implement a framework to archive zip files in an S3 bucket based on configurable rules. The solution must include options for retrieval and notification, while ensuring compatibility with the existing S3 infrastructure.
Key Requirements
1. Retention Policy
- Archive zip files in the S3 bucket after 3 months of their creation date.
2. Exceptions
- Certain files need to be excluded from the archival process based on defined criteria (to be provided later).
3. Framework Design
- Develop a custom framework with the following features:
  - Rule-based archival configuration.
  - Option to choose archival criteria based on:
    - Tags associated with the file.
    - Creation Date of the file.
    - COB Date (Close of Business Date) of the file.
  - Store the configuration in a DynamoDB table with fields like:
    - ConfigId
    - RuleType (e.g., tags, creation date, COB date)
    - Criteria Details (specific rules/values for archival)
    - Description
    - Last Updated.
4. Archival Rules
- Archive only files that:
  - Are in zip format.
  - Meet the criteria set in the rule-based configuration.
5. Script Implementation
- Develop a script capable of running on EC2 to:
  - Read archival configuration from DynamoDB.
  - Identify eligible files based on the rules.
  - Move files to the Amazon S3 Deep Archive.
6. Access and Impact Analysis
- Assess the impact of infrequent access to S3 data.
- Ensure no business disruptions due to archival.
7. Archival Location
- Move archived zip files to Amazon S3 Deep Archive as part of the first release.
8. Retrieval Process
- Implement a mechanism to handle retrieval requests from the Deep Archive:
  - Allow users to request retrieval for specific files.
  - Set up a notification mechanism to inform users when files are available after retrieval.
