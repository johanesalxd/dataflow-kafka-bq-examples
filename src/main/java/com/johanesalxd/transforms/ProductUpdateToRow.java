package com.johanesalxd.transforms;

import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;
import org.json.JSONObject;

public class ProductUpdateToRow extends DoFn<KV<String, String>, Row> {

    // Define the schema for product updates
    public static final Schema SCHEMA = Schema
            .builder()
            .addStringField("product_id")
            .addStringField("product_name")
            .addDoubleField("price")
            .addStringField("category")
            .addDateTimeField("timestamp")
            .build();

    @ProcessElement
    public void processElement(ProcessContext c) {
        String json = c.element().getValue();
        JSONObject jsonObject = new JSONObject(json);

        // Parse the timestamp from the JSON
        Instant timestamp = Instant.parse(jsonObject.getString("timestamp"));

        Row row = Row.withSchema(SCHEMA)
                .addValue(jsonObject.getString("product_id"))
                .addValue(jsonObject.getString("product_name"))
                .addValue(jsonObject.getDouble("price"))
                .addValue(jsonObject.getString("category"))
                .addValue(timestamp)
                .build();

        c.output(row);
    }
}
