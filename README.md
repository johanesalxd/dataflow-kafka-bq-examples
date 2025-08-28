# Dataflow Kafka to BigQuery Examples (Java)

This repository contains a simple, reliable Java-based Apache Beam pipeline that streams data from Kafka to a partitioned BigQuery table.

## Project Structure

```
.
├── pom.xml                                 # Maven project configuration
├── run.sh                                  # Script to run the pipeline
├── src/main/java/com/johanesalxd/          # Java source code
│   ├── KafkaToBigQuery.java                # Main pipeline logic
│   ├── KafkaPipelineOptions.java           # Custom pipeline options
│   └── utils/
│       ├── BigQuerySchema.java             # BigQuery table schema
│       └── JsonToTableRow.java             # Utility to convert JSON to TableRow
├── kafka-tools/                            # Kafka producer/consumer tools
│   ├── data_generator.py
│   └── data_consumer.py
└── schemas/                                # JSON schemas for BigQuery
    └── user_events.json
```

## Quick Start

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

4.  **Run the Pipeline:**
    In another terminal, run the following command to start the Beam pipeline:
    ```bash
    ./run.sh
    ```

The pipeline will start consuming messages from the `user-events` topic and writing them to the `raw_user_events` table in the `dataflow_demo_local` dataset in BigQuery.

## Features

*   **Java-based:** A reliable and robust implementation using the Java SDK.
*   **Simplified Configuration:** All configuration is handled in the `run.sh` script, making it easy to get started.
*   **Partitioned BigQuery Table:** The pipeline writes to a time-partitioned BigQuery table, which is a best practice for managing large datasets.
*   **Clean and Simple Code:** The code is well-structured and easy to understand, making it a great starting point for more complex pipelines.
