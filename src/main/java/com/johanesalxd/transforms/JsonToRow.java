package com.johanesalxd.transforms;

import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;
import org.json.JSONObject;

public class JsonToRow extends DoFn<KV<String, String>, Row> {

    // Define the schema for Beam SQL
    public static final Schema SCHEMA = Schema
            .builder()
            .addStringField("event_id")
            .addStringField("user_id")
            .addStringField("event_type")
            .addNullableStringField("product_id")
            .addDateTimeField("event_time")
            .build();

    @ProcessElement
    public void processElement(ProcessContext c) {
        String json = c.element().getValue();
        JSONObject jsonObject = new JSONObject(json);

        // Parse the timestamp from the JSON
        Instant eventTime = Instant.parse(jsonObject.getString("timestamp"));

        Row row = Row.withSchema(SCHEMA)
                .addValue(jsonObject.getString("event_id"))
                .addValue(jsonObject.getString("user_id"))
                .addValue(jsonObject.getString("event_type"))
                .addValue(jsonObject.optString("product_id", null))
                .addValue(eventTime)
                .build();

        c.output(row);
    }
}
