package com.johanesalxd.schemas;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableSchema;

import java.util.ArrayList;
import java.util.List;

public class ProductUpdateBigQuerySchema {

    public static TableSchema getSchema() {
        List<TableFieldSchema> fields = new ArrayList<>();
        fields.add(new TableFieldSchema().setName("product_id").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("product_name").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("price").setType("FLOAT").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("category").setType("STRING").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("timestamp").setType("TIMESTAMP").setMode("REQUIRED"));
        fields.add(new TableFieldSchema().setName("processing_time").setType("TIMESTAMP").setMode("REQUIRED"));
        return new TableSchema().setFields(fields);
    }
}
