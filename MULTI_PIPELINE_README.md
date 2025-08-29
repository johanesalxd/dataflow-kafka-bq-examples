# Multi-Pipeline Beam Example

This project demonstrates how to implement multiple independent Apache Beam pipelines within a single job, showcasing stream-to-stream joins using Beam SQL.

## Architecture Overview

The implementation consists of two independent pipelines:

### Pipeline 1: User Profiles (Simple Kafka to BigQuery)
- **Source**: Kafka topic `user-profiles`
- **Transform**: Parse JSON to TableRow using generic approach
- **Sink**: BigQuery table for user profiles
- **Purpose**: Demonstrates simple Kafka-to-BigQuery pipeline

### Pipeline 2: Multi-Stream Join with Beam SQL
- **Sources**:
  - Kafka topic `user-events`
  - Kafka topic `product-updates`
  - Kafka topic `user-profiles` (for joining)
- **Transform**: Beam SQL joins across all three streams
- **Sink**: BigQuery table for enriched events
- **Purpose**: Demonstrates complex stream-to-stream joins using SQL

## Data Schemas

### User Events (`user_events.json`)
```json
{
  "event_id": "string",
  "user_id": "string",
  "event_type": "string",
  "product_id": "string (nullable)",
  "timestamp": "timestamp",
  "processing_time": "timestamp"
}
```

### User Profiles (`user_profiles.json`)
```json
{
  "user_id": "string",
  "username": "string",
  "user_segment": "string",
  "registration_date": "date",
  "timestamp": "timestamp",
  "processing_time": "timestamp"
}
```

### Product Updates (`product_updates.json`)
```json
{
  "product_id": "string",
  "product_name": "string",
  "price": "float",
  "category": "string",
  "timestamp": "timestamp",
  "processing_time": "timestamp"
}
```

### Enriched Events (Output)
Combined data from all three sources with fields from user_events, product_updates, and user_profiles.

## SQL Join Logic

The pipeline uses the following SQL query (`enriched_events_join.sql`):

```sql
SELECT
    ue.event_id,
    ue.user_id,
    ue.event_type,
    ue.event_time as event_timestamp,
    pu.product_id,
    pu.product_name,
    pu.price,
    pu.category,
    up.username,
    up.user_segment,
    up.registration_date
FROM user_events ue
LEFT JOIN product_updates pu ON ue.product_id = pu.product_id
LEFT JOIN user_profiles up ON ue.user_id = up.user_id
```

## Key Features

1. **Independent Pipelines**: Two completely separate pipelines that can fail/restart independently
2. **Beam SQL Integration**: Uses Beam SQL for complex joins instead of manual CoGroupByKey
3. **Windowing**: Fixed 1-minute windows for stream processing
4. **Schema Evolution**: Proper schema definitions for all data types
5. **Error Handling**: Nullable fields for optional joins
6. **Scalable Design**: Can be easily extended with additional streams

## Running the Pipeline

### Prerequisites
- Apache Kafka running (external IP accessible)
- Google Cloud Platform project with Dataflow and BigQuery APIs enabled
- GCS bucket for temporary storage
- Maven for building

### Dataflow Deployment
The pipeline is designed for production deployment on Google Cloud Dataflow:

1. **Configure the deployment script:**
   ```bash
   # Edit run_multi_pipeline.sh and set:
   PROJECT_ID="your-project-id"
   TEMP_BUCKET="gs://your-gcs-bucket"
   KAFKA_BOOTSTRAP_SERVERS="EXTERNAL_IP:9092"
   ```

2. **Deploy to Dataflow:**
   ```bash
   ./run_multi_pipeline.sh
   ```

The script will:
- Create GCS bucket and BigQuery dataset if needed
- Create BigQuery tables with proper schemas and partitioning
- Package the pipeline JAR
- Submit the streaming job to Dataflow with optimized settings

### Manual Dataflow Execution
```bash
java -jar target/dataflow-kafka-bq-examples-1.0-SNAPSHOT.jar \
    --runner=DataflowRunner \
    --project=your-project \
    --region=us-central1 \
    --tempLocation=gs://your-bucket/temp \
    --stagingLocation=gs://your-bucket/staging \
    --bootstrapServers=EXTERNAL_IP:9092 \
    --userEventsTopic=user-events \
    --userProfilesTopic=user-profiles \
    --productUpdatesTopic=product-updates \
    --userProfilesTable=project:dataset.user_profiles \
    --enrichedEventsTable=project:dataset.enriched_events \
    --streaming \
    --maxNumWorkers=3
```

## Project Structure

```
src/main/java/com/johanesalxd/
├── MultiPipelineExample.java          # Main pipeline class
├── MultiPipelineOptions.java          # Pipeline options interface
├── schemas/                           # BigQuery schema definitions
│   ├── UserEventBigQuerySchema.java
│   ├── UserProfileBigQuerySchema.java
│   ├── ProductUpdateBigQuerySchema.java
│   └── EnrichedEventBigQuerySchema.java
└── transforms/                        # Data transformation classes
    ├── JsonToRow.java                 # User events to Row
    ├── UserProfileToRow.java          # User profiles to Row
    ├── ProductUpdateToRow.java        # Product updates to Row
    ├── UserProfileToTableRow.java     # User profiles to TableRow
    ├── EnrichedEventToTableRow.java   # Joined data to TableRow
    └── SqlQueryReader.java            # SQL query file reader

src/main/resources/udf/
└── enriched_events_join.sql           # SQL join query
```

## Benefits of This Approach

1. **Modularity**: Each pipeline can be developed, tested, and deployed independently
2. **SQL Simplicity**: Complex joins expressed in familiar SQL syntax
3. **Maintainability**: Clear separation of concerns between data processing logic
4. **Scalability**: Easy to add new data sources or modify join logic
5. **Monitoring**: Independent pipeline metrics and monitoring
6. **Fault Tolerance**: Failure in one pipeline doesn't affect the other

## Next Steps

- Add data validation and error handling
- Implement dead letter queues for failed records
- Add metrics and monitoring
- Consider using BigQuery as a side input for larger reference data
- Implement exactly-once processing guarantees
