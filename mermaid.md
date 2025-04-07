```mermaid
graph TD
    subgraph "Log Sources (Platform Agnostic)"
        LS1[AWS CloudWatch Logs]
        LS2[Azure Monitor Logs]
        LS3[On-Prem Apps / Servers (File Logs)]
        LS4[Kubernetes Cluster Logs]
        LS5[Other Cloud/SaaS Logs]
    end

    subgraph "1. Log Ingestion & Buffering"
        direction LR
        LA[Log Agents/Forwarders <br/> (Fluentd, Logstash, Azure Monitor Agent, CloudWatch Agent, Custom Scripts)]
        LB[Log Buffer/Stream <br/> (Azure Event Hubs / Kafka / AWS Kinesis)]
        LA --> LB
    end

    subgraph "2. Log Processing & Aggregation"
        direction TB
        SA[Stream Processing <br/> (Azure Stream Analytics / Azure Functions / Spark Streaming)]
        AGG[Central Log Aggregation <br/> (Azure Data Explorer (ADX) / Azure Log Analytics Workspace / Elasticsearch)]
        SA -- Structured Logs --> AGG
    end

    subgraph "3. AI Analysis Core (Azure)"
        direction TB
        ORC[Orchestrator <br/> (Azure Logic Apps / Azure Functions)]
        AOAI[Azure OpenAI Service <br/> (GPT models for Analysis, Classification, Summarization, Q&A)]
        KB[Knowledge Base / Historical Data <br/> (Azure Cosmos DB / Azure SQL / Vector DB in Azure AI Search)]
        ML[Optional: Custom ML Models <br/> (Azure Machine Learning for specific anomaly detection)]

        ORC -- Trigger Analysis --> AOAI
        AOAI -- Analyze Logs, Query History --> KB
        AOAI -- Use Custom Models --> ML
        KB -- Provide Historical Context --> AOAI
        ML -- Return Specific Scores/Predictions --> AOAI
        AOAI -- Results (Error, Impact, RCA, TTR) --> ORC
    end

    subgraph "4. Alerting & Presentation"
        direction LR
        ALT[Alerting Engine <br/> (Azure Monitor Alerts / Custom Alerting Service)]
        DASH[Dashboard / UI <br/> (Azure Dashboards / Power BI / Grafana / Custom Web App)]
        NOTIF[Notification Channels <br/> (Email, Teams, Slack, PagerDuty)]
    end

    subgraph "Security & Governance (Cross-Cutting)"
        SEC[Security <br/> (Azure Key Vault, Managed Identities, Azure Policy, Network Security Groups, RBAC)]
    end

    %% Data Flow Arrows
    LS1 --> LA
    LS2 --> LA
    LS3 --> LA
    LS4 --> LA
    LS5 --> LA

    LB --> SA

    SA -- Trigger on New Data --> ORC

    ORC -- Store Analysis Results --> KB
    ORC -- Trigger Alert --> ALT

    ALT --> NOTIF
    DASH -- Query Logs --> AGG
    DASH -- Query Analysis/Incidents --> KB
    DASH -- Query Alert Status --> ALT

    %% Interactions with Security
    LA -- Uses Credentials --> SEC
    LB -- Access Control --> SEC
    SA -- Access Control --> SEC
    AGG -- Encryption, Access --> SEC
    ORC -- Managed Identity --> SEC
    AOAI -- API Keys/Auth --> SEC
    KB -- Encryption, Access --> SEC
    ALT -- Access Control --> SEC
    DASH -- User Authentication --> SEC
```
