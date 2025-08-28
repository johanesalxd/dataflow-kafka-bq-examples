package com.johanesalxd;

import com.johanesalxd.utils.BigQuerySchema;
import com.johanesalxd.utils.JsonToTableRow;
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;
import org.apache.beam.sdk.io.kafka.KafkaIO;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.kafka.common.serialization.StringDeserializer;

public class KafkaToBigQuery {

    public static void main(String[] args) {
        // Create and configure pipeline options.
        KafkaPipelineOptions options = PipelineOptionsFactory.fromArgs(args).withValidation().as(KafkaPipelineOptions.class);
        Pipeline p = Pipeline.create(options);

        p.apply("ReadFromKafka", KafkaIO.<String, String>read()
                .withBootstrapServers(options.getBootstrapServers())
                .withTopic(options.getTopic())
                .withKeyDeserializer(StringDeserializer.class)
                .withValueDeserializer(StringDeserializer.class)
                .withoutMetadata()
        )
        .apply("ParseMessage", ParDo.of(new JsonToTableRow()))
        .apply("WriteToBigQuery", BigQueryIO.writeTableRows()
                .to(options.getOutputTable())
                .withSchema(BigQuerySchema.getSchema())
                .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND)
                .withCreateDisposition(BigQueryIO.Write.CreateDisposition.CREATE_IF_NEEDED)
        );

        // For Dataflow, just submit the job and exit
        // For local DirectRunner, wait until finish
        if (options.getRunner().getName().contains("DataflowRunner")) {
            p.run();
        } else {
            p.run().waitUntilFinish();
        }
    }
}
