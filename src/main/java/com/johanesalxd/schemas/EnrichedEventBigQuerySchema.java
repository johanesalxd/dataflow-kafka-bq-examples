package com.johanesalxd.schemas;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableSchema;

import java.util.ArrayList;
import java.util.List;

public class EnrichedEventBigQuerySchema {

    public static TableSchema getSchema() {
        List<TableFieldSchema> fields = new ArrayList<>();

        // From user_events
        fields.add(new TableFieldSchema().setName("event_id").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("user_id").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("event_type").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("event_timestamp").setType("TIMESTAMP").setMode("REQUIRED"));

        // From product_updates
        fields.add(new TableFieldSchema().setName("product_id").setType("STRING").setMode("NULLABLE"));
        fields.add(new TableFieldSchema().setName("product_name").setType("STRING").setMode("NULLABLE"));
        fields.add(new TableFieldSchema().setName("price").setType("FLOAT").setMode("NULLABLE"));
        fields.add(new TableFieldSchema().setName("category").setType("STRING").setMode("NULLABLE"));

        // From user_profiles (side input)
        fields.add(new TableFieldSchema().setName("username").setType("STRING").setMode("NULLABLE"));
        fields.add(new TableFieldSchema().setName("user_segment").setType("STRING").setMode("NULLABLE"));
        fields.add(new TableFieldSchema().setName("registration_date").setType("DATE").setMode("NULLABLE"));

        // Processing metadata
        fields.add(new TableFieldSchema().setName("processing_time").setType("TIMESTAMP").setMode("REQUIRED"));

        return new TableSchema().setFields(fields);
    }
}
