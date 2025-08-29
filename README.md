# Dataflow Kafka to BigQuery Examples

This repository contains examples for streaming data from Kafka to BigQuery using both custom Java pipelines and Google's pre-built Dataflow templates.

## Project Structure

```
.
├── pom.xml                                 # Maven project configuration
├── run_local.sh                            # Simple local pipeline (Branch 1 only)
├── run_dataflow.sh                         # Simple Dataflow pipeline (Branch 1 only)
├── run_branched_pipeline.sh                # Advanced pipeline with all three branches
├── run_multi_pipeline.sh                   # Multi-stream join pipeline (NEW)
├── run_dataflow_template.sh                # Script to deploy using Dataflow Flex Template
├── MULTI_PIPELINE_README.md                # Documentation for multi-stream joins
├── udf/
│   ├── process.js                          # JavaScript UDF for template transformation
│   └── user_event_aggregations.sql         # SQL query for Beam SQL aggregations
├── src/main/java/com/johanesalxd/          # Java source code
│   ├── KafkaToBigQuery.java                # Main pipeline logic with three branches
│   ├── MultiPipelineExample.java           # Multi-stream join pipeline (NEW)
│   ├── KafkaPipelineOptions.java           # Pipeline options for single-topic
│   ├── MultiPipelineOptions.java           # Pipeline options for multi-stream (NEW)
│   ├── schemas/                            # BigQuery schema definitions
│   │   ├── UserEventBigQuerySchema.java
│   │   ├── GenericBigQuerySchema.java
│   │   ├── UserEventAggregationSchema.java
│   │   ├── UserProfileBigQuerySchema.java  # NEW
│   │   ├── ProductUpdateBigQuerySchema.java # NEW
│   │   └── EnrichedEventBigQuerySchema.java # NEW
│   └── transforms/                         # Data transformation classes
│       ├── JsonToTableRow.java
│       ├── JsonToGenericTableRow.java
│       ├── JsonToRow.java
│       ├── UserProfileToTableRow.java      # NEW
│       ├── UserProfileToRow.java           # NEW
│       ├── ProductUpdateToRow.java         # NEW
│       ├── EnrichedEventToTableRow.java    # NEW
│       └── SqlQueryReader.java
├── kafka-tools/                            # Kafka producer/consumer tools
│   ├── data_generator.py
│   └── data_consumer.py
└── schemas/                                # JSON schemas for BigQuery
    ├── user_events.json
    ├── user_profiles.json                  # NEW
    ├── product_updates.json                # NEW
    ├── enriched_events.json                # NEW
    ├── generic_table.json
    └── user_event_aggregations.json
```

## Pipeline Scripts Overview

This repository provides multiple deployment scripts for different use cases:

### Simple Pipelines (Single Topic → Single Table)
- **`run_local.sh`** - Local development with DirectRunner (Branch 1 only)
- **`run_dataflow.sh`** - Simple Dataflow deployment (Branch 1 only)

### Advanced Pipelines
- **`run_branched_pipeline.sh`** - Single topic with 3 parallel processing branches
- **`run_multi_pipeline.sh`** - Multi-stream joins with Beam SQL (NEW)
- **`run_dataflow_template.sh`** - Google's managed Flex Template

### Branch Behavior in KafkaToBigQuery.java

The `KafkaToBigQuery.java` pipeline has three conditional branches:

| Branch | Trigger | Purpose | Output |
|--------|---------|---------|---------|
| **Branch 1** | Always runs (requires `outputTable`) | Flattened structured data | `raw_user_events` |
| **Branch 2** | Only if `genericOutputTable` provided | Raw JSON with timestamps | `raw_user_events_flex` |
| **Branch 3** | Only if `sqlAggregationTable` provided | Real-time SQL aggregations | `user_event_aggregations` |

- **Simple scripts** (`run_local.sh`, `run_dataflow.sh`) only provide `outputTable` → Branch 1 only
- **Branched script** (`run_branched_pipeline.sh`) provides all three tables → All branches run
- **Multi-pipeline script** (`run_multi_pipeline.sh`) runs completely different pipeline (`MultiPipelineExample.java`)

### ⚠️ Critical: Main Class Execution

**IMPORTANT**: All scripts use explicit main class specification since no main class is defined in the JAR manifest:

```bash
# ✅ CORRECT - Only method that works
java -cp ${JAR_FILE} com.johanesalxd.KafkaToBigQuery

# ❌ FAILS - No main class in JAR manifest
java -jar ${JAR_FILE}
java -jar ${JAR_FILE} com.johanesalxd.KafkaToBigQuery  # Still fails!
```

**Why this approach:**
- The JAR manifest has **no main class** defined (removed from pom.xml for safety)
- Using `java -jar` will **always fail** with "no main manifest attribute" error
- Only `java -cp` with explicit main class works
- This prevents accidentally running the wrong pipeline

**Benefits:**
- **Explicit Control**: Must specify which main class to run
- **No Ambiguity**: Cannot accidentally run the wrong pipeline
- **Consistency**: All scripts use the same execution method (`java -cp`)
- **Safety**: Impossible to run without explicitly choosing the pipeline

## Quick Start

This repository provides multiple approaches for streaming Kafka data to BigQuery:

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

### Option 4: Multi-Stream Join Pipeline (NEW)

For demonstrating advanced stream processing with multiple Kafka topics and Beam SQL joins:

1.  **Start Kafka:** (same as above)
2.  **Generate Sample Data for Multiple Topics:**
    ```bash
    # Generate data for all three topics
    python3 kafka-tools/data_generator.py --topics user-events,user-profiles,product-updates
    ```
3.  **Deploy Multi-Stream Pipeline:**
    ```bash
    # Edit run_multi_pipeline.sh with your GCP settings
    ./run_multi_pipeline.sh
    ```

This pipeline demonstrates **two independent pipelines** running in the same job:
- **Pipeline 1**: Simple `user-profiles` → BigQuery (demonstrates basic multi-pipeline)
- **Pipeline 2**: Complex multi-stream join using Beam SQL:
  - Reads from `user-events`, `product-updates`, and `user-profiles` topics
  - Performs LEFT JOINs using Beam SQL
  - Outputs enriched events with user and product information

**Key Features:**
- Independent pipeline execution (one can fail without affecting the other)
- Stream-to-stream joins with 1-minute windows
- Beam SQL for complex join logic
- Enriched output combining all three data sources

See `MULTI_PIPELINE_README.md` for detailed documentation.

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
