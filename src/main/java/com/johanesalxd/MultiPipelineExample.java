package com.johanesalxd;

import com.johanesalxd.schemas.UserProfileBigQuerySchema;
import com.johanesalxd.schemas.EnrichedEventBigQuerySchema;
import com.johanesalxd.transforms.JsonToRow;
import com.johanesalxd.transforms.UserProfileToTableRow;
import com.johanesalxd.transforms.UserProfileToRow;
import com.johanesalxd.transforms.ProductUpdateToRow;
import com.johanesalxd.transforms.EnrichedEventToTableRow;
import com.johanesalxd.transforms.SqlQueryReader;
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;
import org.apache.beam.sdk.io.kafka.KafkaIO;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.beam.sdk.transforms.windowing.FixedWindows;
import org.apache.beam.sdk.transforms.windowing.Window;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.PCollectionTuple;
import org.apache.beam.sdk.values.Row;
import org.apache.beam.sdk.values.TupleTag;
import org.apache.beam.sdk.values.TupleTagList;
import org.apache.beam.sdk.extensions.sql.SqlTransform;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.joda.time.Duration;

import java.util.HashMap;
import java.util.Map;

public class MultiPipelineExample {

    public static void main(String[] args) {
        // Create and configure pipeline options
        MultiPipelineOptions options = PipelineOptionsFactory.fromArgs(args).withValidation().as(MultiPipelineOptions.class);
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

        // ========== PIPELINE 1: User Profiles to BigQuery (Simple Kafka to BQ) ==========
        if (options.getUserProfilesTable() != null && options.getUserProfilesTopic() != null) {
            p.apply("ReadUserProfilesFromKafka", KafkaIO.<String, String>read()
                    .withBootstrapServers(options.getBootstrapServers())
                    .withTopic(options.getUserProfilesTopic())
                    .withKeyDeserializer(StringDeserializer.class)
                    .withValueDeserializer(StringDeserializer.class)
                    .withConsumerConfigUpdates(consumerConfig)
                    .withoutMetadata()
            )
            .apply("ParseUserProfilesToTableRow", ParDo.of(new UserProfileToTableRow()))
            .apply("WriteUserProfilesToBQ", BigQueryIO.writeTableRows()
                    .to(options.getUserProfilesTable())
                    .withSchema(UserProfileBigQuerySchema.getSchema())
                    .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND)
                    .withCreateDisposition(BigQueryIO.Write.CreateDisposition.CREATE_IF_NEEDED)
            );
        }

        // ========== PIPELINE 2: Multi-Stream Join with Beam SQL ==========
        if (options.getEnrichedEventsTable() != null &&
            options.getUserEventsTopic() != null &&
            options.getProductUpdatesTopic() != null &&
            options.getUserProfilesTopic() != null) {

            // Read user events from Kafka
            PCollection<Row> userEvents = p.apply("ReadUserEventsFromKafka", KafkaIO.<String, String>read()
                    .withBootstrapServers(options.getBootstrapServers())
                    .withTopic(options.getUserEventsTopic())
                    .withKeyDeserializer(StringDeserializer.class)
                    .withValueDeserializer(StringDeserializer.class)
                    .withConsumerConfigUpdates(consumerConfig)
                    .withoutMetadata()
            )
            .apply("ParseUserEventsToRow", ParDo.of(new JsonToRow()))
            .setRowSchema(JsonToRow.SCHEMA)
            .apply("WindowUserEvents", Window.<Row>into(FixedWindows.of(Duration.standardMinutes(1))));

            // Read product updates from Kafka
            PCollection<Row> productUpdates = p.apply("ReadProductUpdatesFromKafka", KafkaIO.<String, String>read()
                    .withBootstrapServers(options.getBootstrapServers())
                    .withTopic(options.getProductUpdatesTopic())
                    .withKeyDeserializer(StringDeserializer.class)
                    .withValueDeserializer(StringDeserializer.class)
                    .withConsumerConfigUpdates(consumerConfig)
                    .withoutMetadata()
            )
            .apply("ParseProductUpdatesToRow", ParDo.of(new ProductUpdateToRow()))
            .setRowSchema(ProductUpdateToRow.SCHEMA)
            .apply("WindowProductUpdates", Window.<Row>into(FixedWindows.of(Duration.standardMinutes(1))));

            // Read user profiles from Kafka (for joining)
            PCollection<Row> userProfiles = p.apply("ReadUserProfilesForJoinFromKafka", KafkaIO.<String, String>read()
                    .withBootstrapServers(options.getBootstrapServers())
                    .withTopic(options.getUserProfilesTopic())
                    .withKeyDeserializer(StringDeserializer.class)
                    .withValueDeserializer(StringDeserializer.class)
                    .withConsumerConfigUpdates(consumerConfig)
                    .withoutMetadata()
            )
            .apply("ParseUserProfilesForJoinToRow", ParDo.of(new UserProfileToRow()))
            .setRowSchema(UserProfileToRow.SCHEMA)
            .apply("WindowUserProfiles", Window.<Row>into(FixedWindows.of(Duration.standardMinutes(1))));

            // Create tuple tags for SQL join
            TupleTag<Row> userEventsTag = new TupleTag<Row>("user_events"){};
            TupleTag<Row> productUpdatesTag = new TupleTag<Row>("product_updates"){};
            TupleTag<Row> userProfilesTag = new TupleTag<Row>("user_profiles"){};

            // Combine all streams for SQL join
            PCollectionTuple inputs = PCollectionTuple.of(userEventsTag, userEvents)
                    .and(productUpdatesTag, productUpdates)
                    .and(userProfilesTag, userProfiles);

            // Apply SQL join
            inputs.apply("JoinStreamsWithSQL", SqlTransform.query(
                    SqlQueryReader.readQuery("enriched_events_join.sql")))
            .apply("ConvertToEnrichedTableRows", ParDo.of(new EnrichedEventToTableRow()))
            .apply("WriteEnrichedEventsToBQ", BigQueryIO.writeTableRows()
                    .to(options.getEnrichedEventsTable())
                    .withSchema(EnrichedEventBigQuerySchema.getSchema())
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
