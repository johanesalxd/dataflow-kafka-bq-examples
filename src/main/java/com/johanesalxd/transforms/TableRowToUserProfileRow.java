package com.johanesalxd.transforms;

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;
import org.joda.time.format.DateTimeFormat;
import org.joda.time.format.DateTimeFormatter;

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

    // BigQuery timestamp format: "2025-08-29 01:22:02.514805 UTC"
    private static final DateTimeFormatter BIGQUERY_TIMESTAMP_FORMATTER =
            DateTimeFormat.forPattern("yyyy-MM-dd HH:mm:ss.SSSSSS 'UTC'");

    @ProcessElement
    public void processElement(ProcessContext c) {
        TableRow tableRow = c.element();

        // Parse timestamp from BigQuery format
        String timestampStr = (String) tableRow.get("timestamp");
        Instant timestamp;
        try {
            // Try BigQuery format first
            timestamp = BIGQUERY_TIMESTAMP_FORMATTER.parseDateTime(timestampStr).toInstant();
        } catch (Exception e) {
            try {
                // Fallback to ISO format
                timestamp = Instant.parse(timestampStr);
            } catch (Exception e2) {
                // If both fail, use current time and log warning
                timestamp = Instant.now();
                System.err.println("Warning: Could not parse timestamp '" + timestampStr +
                                 "', using current time. Original error: " + e.getMessage());
            }
        }

        // Convert BigQuery TableRow to Beam Row
        Row row = Row.withSchema(SCHEMA)
                .addValue((String) tableRow.get("user_id"))
                .addValue((String) tableRow.get("username"))
                .addValue((String) tableRow.get("user_segment"))
                .addValue((String) tableRow.get("registration_date"))
                .addValue(timestamp)
                .build();

        c.output(row);
    }
}
