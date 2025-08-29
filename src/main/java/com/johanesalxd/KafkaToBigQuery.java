package com.johanesalxd;

import com.johanesalxd.schemas.UserEventBigQuerySchema;
import com.johanesalxd.schemas.GenericBigQuerySchema;
import com.johanesalxd.transforms.JsonToTableRow;
import com.johanesalxd.transforms.JsonToGenericTableRow;
import com.johanesalxd.transforms.JsonToRow;
import com.johanesalxd.transforms.SqlQueryReader;
import com.johanesalxd.schemas.UserEventAggregationSchema;
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;
import org.apache.beam.sdk.io.kafka.KafkaIO;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.beam.sdk.transforms.windowing.FixedWindows;
import org.apache.beam.sdk.transforms.windowing.Window;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.Row;
import org.apache.beam.sdk.extensions.sql.SqlTransform;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import com.google.api.services.bigquery.model.TableRow;
import org.joda.time.Duration;
import org.joda.time.Instant;

import java.util.HashMap;
import java.util.Map;

public class KafkaToBigQuery {

    public static void main(String[] args) {
        // Create and configure pipeline options.
        KafkaPipelineOptions options = PipelineOptionsFactory.fromArgs(args).withValidation().as(KafkaPipelineOptions.class);
        Pipeline p = Pipeline.create(options);

        // Configure Kafka consumer properties
        Map<String, Object> consumerConfig = new HashMap<>();
        if (options.getConsumerGroupId() != null) {
            consumerConfig.put(ConsumerConfig.GROUP_ID_CONFIG, options.getConsumerGroupId());
        }

        // Set Kafka read offset (default to latest if not specified)
        String kafkaOffset = options.getKafkaReadOffset();
        if (kafkaOffset != null && kafkaOffset.equalsIgnoreCase("earliest")) {
            consumerConfig.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        } else {
            consumerConfig.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        }

        // Read from Kafka once - this will be the source for both branches
        PCollection<KV<String, String>> kafkaMessages = p.apply("ReadFromKafka", KafkaIO.<String, String>read()
                .withBootstrapServers(options.getBootstrapServers())
                .withTopic(options.getTopic())
                .withKeyDeserializer(StringDeserializer.class)
                .withValueDeserializer(StringDeserializer.class)
                .withConsumerConfigUpdates(consumerConfig)
                .withoutMetadata()
        );

        // Branch 1: Existing flattened approach
        kafkaMessages
                .apply("ParseToFlattened", ParDo.of(new JsonToTableRow()))
                .apply("WriteToFlattenedTable", BigQueryIO.writeTableRows()
                        .to(options.getOutputTable())
                        .withSchema(UserEventBigQuerySchema.getSchema())
                        .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND)
                        .withCreateDisposition(BigQueryIO.Write.CreateDisposition.CREATE_IF_NEEDED)
                );

        // Branch 2: New generic approach (only if generic output table is specified). Table created by the startup script
        if (options.getGenericOutputTable() != null) {
            kafkaMessages
                    .apply("ParseToGeneric", ParDo.of(new JsonToGenericTableRow()))
                    .apply("WriteToGenericTable", BigQueryIO.writeTableRows()
                            .to(options.getGenericOutputTable())
                            .withSchema(GenericBigQuerySchema.getSchema())
                            .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND)
                    );
        }

        // Branch 3: Beam SQL aggregation (only if SQL aggregation table is specified)
        if (options.getSqlAggregationTable() != null) {
            kafkaMessages
                    .apply("ParseToRows", ParDo.of(new JsonToRow()))
                    .setRowSchema(JsonToRow.SCHEMA)
                    .apply("ApplyWindowing", Window.<Row>into(FixedWindows.of(Duration.standardMinutes(1))))
                    .apply("SqlAggregation", SqlTransform.query(
                            SqlQueryReader.readQuery("user_event_aggregations.sql")))
                    .apply("ConvertToTableRows", ParDo.of(new DoFn<Row, TableRow>() {
                        @ProcessElement
                        public void processElement(ProcessContext c) {
                            Row row = c.element();
                            TableRow tableRow = new TableRow();
                            tableRow.set("event_type", row.getString("event_type"));
                            tableRow.set("event_count", row.getInt64("event_count"));
                            tableRow.set("window_start", row.getDateTime("window_start").toString());
                            tableRow.set("window_end", row.getDateTime("window_end").toString());
                            tableRow.set("processing_time", Instant.now().toString());
                            c.output(tableRow);
                        }
                    }))
                    .apply("WriteToAggregationTable", BigQueryIO.writeTableRows()
                            .to(options.getSqlAggregationTable())
                            .withSchema(UserEventAggregationSchema.getSchema())
                            .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND)
                            .withCreateDisposition(BigQueryIO.Write.CreateDisposition.CREATE_IF_NEEDED)
                    );
        }

        // For Dataflow, just submit the job and exit
        // For local DirectRunner, wait until finish
        if (options.getRunner().getName().contains("DataflowRunner")) {
            p.run();
        } else {
            p.run().waitUntilFinish();
        }
    }
}
