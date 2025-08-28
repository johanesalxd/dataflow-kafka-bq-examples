# Dataflow Kafka to BigQuery Examples

This repository contains examples for streaming data from Kafka to BigQuery using both custom Java pipelines and Google's pre-built Dataflow templates.

## Project Structure

```
.
├── pom.xml                                 # Maven project configuration
├── run_local.sh                            # Script to run the custom Java pipeline locally
├── run_dataflow.sh                         # Script to deploy custom Java pipeline to Dataflow
├── run_branched_pipeline.sh                # Script to deploy pipeline with all three branches
├── run_dataflow_template.sh                # Script to deploy using Dataflow Flex Template
├── udf/
│   ├── process.js                          # JavaScript UDF for template transformation
│   └── user_event_aggregations.sql         # SQL query for Beam SQL aggregations
├── src/main/java/com/johanesalxd/          # Java source code
│   ├── KafkaToBigQuery.java                # Main pipeline logic with three branches
│   ├── KafkaPipelineOptions.java           # Custom pipeline options
│   └── utils/
│       ├── BigQuerySchema.java             # BigQuery table schema
│       ├── GenericBigQuerySchema.java      # Generic table schema
│       ├── UserEventAggregationSchema.java # SQL aggregation table schema
│       ├── JsonToTableRow.java             # Utility to convert JSON to TableRow
│       ├── JsonToGenericTableRow.java      # Utility for generic table
│       ├── JsonToRow.java                  # Utility for Beam SQL Row format
│       └── SqlQueryReader.java             # Utility to read SQL files
├── kafka-tools/                            # Kafka producer/consumer tools
│   ├── data_generator.py
│   └── data_consumer.py
└── schemas/                                # JSON schemas for BigQuery
    ├── user_events.json
    ├── generic_table.json                  # Schema for template-based pipeline
    └── user_event_aggregations.json        # Schema for SQL aggregations
```

## Quick Start

This repository provides two approaches for streaming Kafka data to BigQuery:

### Option 1: Custom Java Pipeline (Local Development)

1.  **Start Kafka:**
    ```bash
    docker-compose up -d
    ```

2.  **Install Java and Maven:**
    This project requires Java 11 and Maven to be installed on your system.

3.  **Generate Sample Data:**
    In a separate terminal, run the data generator to start producing messages to the `user-events` topic:
    ```bash
    python3 kafka-tools/data_generator.py --topics user-events
    ```

4.  **Run the Pipeline Locally:**
    In another terminal, run the following command to start the Beam pipeline locally:
    ```bash
    ./run_local.sh
    ```

The pipeline will start consuming messages from the `user-events` topic and writing them to the `raw_user_events` table in the `dataflow_demo_local` dataset in BigQuery.

### Option 2: Dataflow Flex Template (Production Ready)

For a simpler deployment without Java/Maven requirements:

1.  **Start Kafka:** (same as above)
2.  **Generate Sample Data:** (same as above)
3.  **Configure and Deploy:**
    ```bash
    # Edit run_dataflow_template.sh with your GCP settings
    ./run_dataflow_template.sh
    ```

This approach uses Google's managed template and writes to the `raw_user_events_flex` table.

### Option 3: Multi-Branch Pipeline with Beam SQL (Advanced)

For demonstrating multiple processing approaches including real-time SQL aggregations:

1.  **Start Kafka:** (same as above)
2.  **Generate Sample Data:** (same as above)
3.  **Deploy Multi-Branch Pipeline:**
    ```bash
    # Edit run_branched_pipeline.sh with your GCP settings
    ./run_branched_pipeline.sh
    ```

This pipeline processes the same Kafka stream into **three parallel branches**:
- **Flattened events** → `raw_user_events` (structured schema)
- **Generic events** → `raw_user_events_flex` (raw JSON with timestamps)
- **SQL aggregations** → `user_event_aggregations` (real-time event counts by type)

The SQL aggregation branch demonstrates **Beam SQL** capabilities with 1-minute tumbling windows, counting events by type using the query in `udf/user_event_aggregations.sql`.

## Deploying to Google Cloud Dataflow

For production deployments, you can run the same pipeline on Google Cloud Dataflow:

For a simpler deployment without Java/Maven requirements:

1.  **Start Kafka:** (same as above)
2.  **Generate Sample Data:** (same as above)
3.  **Configure and Deploy:**
    ```bash
    # Edit run_dataflow_template.sh with your GCP settings
    ./run_dataflow.sh
    ```

This approach uses Google's managed template and writes to the `raw_user_events` table.

### Monitoring
- View jobs: [Dataflow Console](https://console.cloud.google.com/dataflow)
- Monitor data: [BigQuery Console](https://console.cloud.google.com/bigquery)

## Using Dataflow Flex Template (Alternative Approach)

For users who prefer to use Google's pre-built templates instead of custom Java code, this repository also includes a template-based approach using the `Kafka_to_BigQuery_Flex` template.

### Template vs Custom Pipeline Comparison

| Feature | Custom Java Pipeline | Dataflow Flex Template |
|---------|---------------------|------------------------|
| **Setup** | Requires Java 11 + Maven | Only requires gcloud CLI |
| **Deployment** | Compile + Deploy | Direct deployment |
| **Customization** | Full Java flexibility | JavaScript UDF only |
| **Maintenance** | User maintains code | Google maintains template |
| **Table Schema** | Custom schema | Generic schema with payload |
| **Output Table** | `raw_user_events` | `raw_user_events_flex` |

## Features

*   **Java-based:** A reliable and robust implementation using the Java SDK.
*   **Multi-Branch Processing:** Single pipeline with three parallel processing branches for different use cases.
*   **Beam SQL Integration:** Real-time SQL aggregations with external query files for easy maintenance.
*   **Simplified Configuration:** All configuration is handled in the deployment scripts, making it easy to get started.
*   **Partitioned BigQuery Tables:** All pipelines write to time-partitioned BigQuery tables, which is a best practice for managing large datasets.
*   **Clean and Simple Code:** The code is well-structured and easy to understand, making it a great starting point for more complex pipelines.
*   **Flexible Schema Management:** Support for both structured and generic schemas with automatic table creation.
