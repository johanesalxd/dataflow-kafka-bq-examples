package com.johanesalxd.transforms;

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;

public class EnrichedEventToTableRow extends DoFn<Row, TableRow> {

    @ProcessElement
    public void processElement(ProcessContext c) {
        Row row = c.element();
        TableRow tableRow = new TableRow();

        // From user_events
        tableRow.set("event_id", row.getString("event_id"));
        tableRow.set("user_id", row.getString("user_id"));
        tableRow.set("event_type", row.getString("event_type"));
        tableRow.set("event_timestamp", row.getDateTime("event_timestamp").toString());

        // From product_updates (nullable)
        if (row.getValue("product_id") != null) {
            tableRow.set("product_id", row.getString("product_id"));
            tableRow.set("product_name", row.getString("product_name"));
            tableRow.set("price", row.getDouble("price"));
            tableRow.set("category", row.getString("category"));
        }

        // From user_profiles (nullable)
        if (row.getValue("username") != null) {
            tableRow.set("username", row.getString("username"));
            tableRow.set("user_segment", row.getString("user_segment"));
            tableRow.set("registration_date", row.getString("registration_date"));
        }

        // Processing metadata
        tableRow.set("processing_time", Instant.now().toString());

        c.output(tableRow);
    }
}
