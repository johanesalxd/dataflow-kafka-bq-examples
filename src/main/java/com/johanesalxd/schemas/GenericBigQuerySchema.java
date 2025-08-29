package com.johanesalxd.schemas;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableSchema;

import java.util.ArrayList;
import java.util.List;

public class GenericBigQuerySchema {

    public static TableSchema getSchema() {
        List<TableFieldSchema> fields = new ArrayList<>();
        fields.add(new TableFieldSchema().setName("event_time").setType("TIMESTAMP").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("processing_time").setType("TIMESTAMP").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("payload").setType("JSON").setMode("NULLABLE"));
        return new TableSchema().setFields(fields);
    }
}
