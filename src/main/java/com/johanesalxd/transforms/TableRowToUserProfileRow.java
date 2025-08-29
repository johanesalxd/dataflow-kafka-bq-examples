package com.johanesalxd.transforms;

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;

/**
 * Transform to convert BigQuery TableRow to Row with user profile schema.
 * This is used when reading user profiles from BigQuery as a side input.
 */
public class TableRowToUserProfileRow extends DoFn<TableRow, Row> {

    // Define the schema for user profiles (same as UserProfileToRow.SCHEMA)
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
        TableRow tableRow = c.element();

        // Convert BigQuery TableRow to Beam Row
        Row row = Row.withSchema(SCHEMA)
                .addValue((String) tableRow.get("user_id"))
                .addValue((String) tableRow.get("username"))
                .addValue((String) tableRow.get("user_segment"))
                .addValue((String) tableRow.get("registration_date"))
                .addValue(Instant.parse((String) tableRow.get("timestamp")))
                .build();

        c.output(row);
    }
}
