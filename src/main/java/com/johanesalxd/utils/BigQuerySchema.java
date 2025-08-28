package com.johanesalxd.utils;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableSchema;

import java.util.ArrayList;
import java.util.List;

public class BigQuerySchema {

    public static TableSchema getSchema() {
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
