package com.johanesalxd;

import org.apache.beam.sdk.options.Description;
import org.apache.beam.sdk.options.PipelineOptions;

public interface KafkaPipelineOptions extends PipelineOptions {
    @Description("Kafka bootstrap servers")
    String getBootstrapServers();
    void setBootstrapServers(String value);

    @Description("Kafka topic")
    String getTopic();
    void setTopic(String value);

    @Description("BigQuery output table")
    String getOutputTable();
    void setOutputTable(String value);

    @Description("Kafka consumer group ID")
    String getConsumerGroupId();
    void setConsumerGroupId(String value);
}
