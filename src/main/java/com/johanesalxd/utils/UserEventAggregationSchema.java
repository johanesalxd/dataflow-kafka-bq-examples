package com.johanesalxd.utils;

import com.google.api.services.bigquery.model.TableFieldSchema;
import com.google.api.services.bigquery.model.TableSchema;

import java.util.ArrayList;
import java.util.List;

public class UserEventAggregationSchema {

    public static TableSchema getSchema() {
        List<TableFieldSchema> fields = new ArrayList<>();

        fields.add(new TableFieldSchema()
                .setName("event_type")
                .setType("STRING")
                .setMode("REQUIRED")
                .setDescription("Type of event being aggregated"));

        fields.add(new TableFieldSchema()
                .setName("event_count")
                .setType("INTEGER")
                .setMode("REQUIRED")
                .setDescription("Number of events in the aggregation window"));

        fields.add(new TableFieldSchema()
                .setName("window_start")
                .setType("TIMESTAMP")
                .setMode("REQUIRED")
                .setDescription("Start timestamp of the aggregation window"));

        fields.add(new TableFieldSchema()
                .setName("window_end")
                .setType("TIMESTAMP")
                .setMode("REQUIRED")
                .setDescription("End timestamp of the aggregation window"));

        fields.add(new TableFieldSchema()
                .setName("processing_time")
                .setType("TIMESTAMP")
                .setMode("REQUIRED")
                .setDescription("Pipeline processing timestamp"));

        return new TableSchema().setFields(fields);
    }
}
