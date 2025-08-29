package com.johanesalxd;

import org.apache.beam.sdk.options.Description;

public interface MultiPipelineOptions extends KafkaPipelineOptions {

    // Topics for the multi-pipeline
    @Description("Kafka topic for user events")
    String getUserEventsTopic();
    void setUserEventsTopic(String value);

    @Description("Kafka topic for user profiles")
    String getUserProfilesTopic();
    void setUserProfilesTopic(String value);

    @Description("Kafka topic for product updates")
    String getProductUpdatesTopic();
    void setProductUpdatesTopic(String value);

    // BigQuery tables for outputs
    @Description("BigQuery table for user profiles (generic storage)")
    String getUserProfilesTable();
    void setUserProfilesTable(String value);

    @Description("BigQuery table for enriched events (joined data)")
    String getEnrichedEventsTable();
    void setEnrichedEventsTable(String value);

    // BigQuery configuration for side input
    @Description("BigQuery project ID for side input reads")
    String getBigQueryProject();
    void setBigQueryProject(String value);

    @Description("BigQuery dataset for side input reads")
    String getBigQueryDataset();
    void setBigQueryDataset(String value);
}
