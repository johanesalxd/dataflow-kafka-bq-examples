package com.johanesalxd;

import com.johanesalxd.utils.BigQuerySchema;
import com.johanesalxd.utils.GenericBigQuerySchema;
import com.johanesalxd.utils.JsonToTableRow;
import com.johanesalxd.utils.JsonToGenericTableRow;
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;
import org.apache.beam.sdk.io.kafka.KafkaIO;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.PCollection;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.clients.consumer.ConsumerConfig;

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
                        .withSchema(BigQuerySchema.getSchema())
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

        // For Dataflow, just submit the job and exit
        // For local DirectRunner, wait until finish
        if (options.getRunner().getName().contains("DataflowRunner")) {
            p.run();
        } else {
            p.run().waitUntilFinish();
        }
    }
}
