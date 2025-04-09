|| Step No. || Component || Description ||
| 1 |  Authentication App | Users authenticate via *Authentication App*, which is specific to your bank. |
| 2 | React Frontend Service (UI) | Receives chat prompt from users after authentication. |
| 3 | Guardrails | Applies safety checks and filters on the chat prompt to ensure compliance and alignment with internal policies. |
| 4 | Python FastAPI Backend Service | Receives the validated prompt from frontend and orchestrates processing. |
| 5 | LlamaIndex Agent | Called by FastAPI service to retrieve schema context for Text2SQL generation. |
| 6 | Knowledgebase (Vectorstore/OpenSearch) | Provides schema-level data to LlamaIndex from vector embeddings. |
| 7 | Knowledgebase Bucket | Stores database/table info in markdown format (KMS-CMK encrypted) that feeds the vector store. |
| 8 | AWS Bedrock LLMs | Receives prompt + schema context and generates the SQL query. |
| 9 | Athena | Executes the generated SQL query against data cataloged in *EDP Central Catalog*. |
| 10 | React Frontend Service (UI) | Receives final LLM response and displays results to the user. |
| 11 | AWS RDS Postgres DB | Stores prompt-response-feedback for conversation memory (KMS-CMK encrypted). |
| 12 | CloudWatch Logging | Logs application and infrastructure-level activity (including ECS and LLM responses). |
| 13 | CloudWatch Metrics + Dashboards | Uses log data to generate dashboards and metrics. |
| 14 | Bedrock Logging Bucket | Stores LLM-specific logs, encrypted using KMS-CMK. |
