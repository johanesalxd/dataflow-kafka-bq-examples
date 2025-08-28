package com.example;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableRow;
import com.google.api.services.bigquery.model.TableSchema;
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.io.gcp.bigquery.BigQueryIO;
import org.apache.beam.sdk.io.kafka.KafkaIO;
import org.apache.beam.sdk.options.PipelineOptions;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.transforms.ParDo;
import org.apache.beam.sdk.values.KV;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.json.JSONObject;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class KafkaToBigQuery {

    public interface KafkaToBigQueryOptions extends PipelineOptions {
    }

    public static void main(String[] args) {
        KafkaToBigQueryOptions options = PipelineOptionsFactory.fromArgs(args).withValidation().as(KafkaToBigQueryOptions.class);
        Pipeline p = Pipeline.create(options);

        p.apply("ReadFromKafka", KafkaIO.<String, String>read()
                .withBootstrapServers("localhost:9092")
                .withTopic("user-events")
                .withKeyDeserializer(StringDeserializer.class)
                .withValueDeserializer(StringDeserializer.class)
                .withoutMetadata()
        )
        .apply("ParseMessage", ParDo.of(new DoFn<KV<String, String>, TableRow>() {
            @ProcessElement
            public void processElement(ProcessContext c) {
                String json = c.element().getValue();
                JSONObject jsonObject = new JSONObject(json);
                TableRow row = new TableRow();
                row.set("event_id", jsonObject.getString("event_id"));
                row.set("user_id", jsonObject.getString("user_id"));
                row.set("event_type", jsonObject.getString("event_type"));
                row.set("product_id", jsonObject.optString("product_id"));
                row.set("timestamp", jsonObject.getString("timestamp"));
                row.set("processing_time", Instant.now().toString());
                c.output(row);
            }
        }))
        .apply("WriteToBigQuery", BigQueryIO.writeTableRows()
                .to("johanesa-playground-326616:dataflow_demo_local.raw_user_events")
                .withSchema(getSchema())
                .withWriteDisposition(BigQueryIO.Write.WriteDisposition.WRITE_APPEND)
                .withCreateDisposition(BigQueryIO.Write.CreateDisposition.CREATE_IF_NEEDED)
        );

        p.run().waitUntilFinish();
    }

    private static TableSchema getSchema() {
        List<TableFieldSchema> fields = new ArrayList<>();
        fields.add(new TableFieldSchema().setName("event_id").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("user_id").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("event_type").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("product_id").setType("STRING").setMode("NULLABLE"));
        fields.add(new TableFieldSchema().setName("timestamp").setType("TIMESTAMP").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("processing_time").setType("TIMESTAMP").setMode("REQUIRED"));
        return new TableSchema().setFields(fields);
    }
}
