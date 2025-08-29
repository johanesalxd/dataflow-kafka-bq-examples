package com.johanesalxd.transforms;

import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;
import org.json.JSONObject;

public class UserProfileToRow extends DoFn<KV<String, String>, Row> {

    // Define the schema for user profiles
    public static final Schema SCHEMA = Schema
            .builder()
            .addStringField("user_id")
            .addStringField("username")
            .addStringField("user_segment")
            .addStringField("registration_date")
            .addDateTimeField("timestamp")
            .build();

    @ProcessElement
    public void processElement(ProcessContext c) {
        String json = c.element().getValue();
        JSONObject jsonObject = new JSONObject(json);

        // Parse the timestamp from the JSON
        Instant timestamp = Instant.parse(jsonObject.getString("timestamp"));

        Row row = Row.withSchema(SCHEMA)
                .addValue(jsonObject.getString("user_id"))
                .addValue(jsonObject.getString("username"))
                .addValue(jsonObject.getString("user_segment"))
                .addValue(jsonObject.getString("registration_date"))
                .addValue(timestamp)
                .build();

        c.output(row);
    }
}
