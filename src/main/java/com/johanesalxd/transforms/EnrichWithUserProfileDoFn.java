package com.johanesalxd.transforms;

import org.apache.beam.sdk.schemas.Schema;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.PCollectionView;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;

import java.util.Map;

/**
 * DoFn to enrich events with user profile data from a side input.
 * Takes the result of the SQL join (events + products) and adds user profile information.
 */
public class EnrichWithUserProfileDoFn extends DoFn<Row, Row> {

    private final PCollectionView<Map<String, Row>> userProfilesView;

    // Schema for the enriched output (events + products + user profiles)
    public static final Schema ENRICHED_SCHEMA = Schema
            .builder()
            .addStringField("event_id")
            .addStringField("user_id")
            .addStringField("event_type")
            .addDateTimeField("event_timestamp")
            .addNullableStringField("product_id")
            .addNullableStringField("product_name")
            .addNullableDoubleField("price")
            .addNullableStringField("category")
            .addNullableStringField("username")
            .addNullableStringField("user_segment")
            .addNullableStringField("registration_date")
            .addDateTimeField("processing_time")
            .build();

    public EnrichWithUserProfileDoFn(PCollectionView<Map<String, Row>> userProfilesView) {
        this.userProfilesView = userProfilesView;
    }

    @ProcessElement
    public void processElement(ProcessContext c) {
        Row eventProductRow = c.element();
        Map<String, Row> userProfiles = c.sideInput(userProfilesView);

        // Get user_id from the event
        String userId = eventProductRow.getString("user_id");

        // Look up user profile from side input
        Row userProfile = userProfiles.get(userId);

        // Create enriched row with all fields
        Row.Builder enrichedRowBuilder = Row.withSchema(ENRICHED_SCHEMA)
                .addValue(eventProductRow.getString("event_id"))
                .addValue(eventProductRow.getString("user_id"))
                .addValue(eventProductRow.getString("event_type"))
                .addValue(eventProductRow.getDateTime("event_timestamp"))
                .addValue(eventProductRow.getString("product_id"))
                .addValue(eventProductRow.getString("product_name"))
                .addValue(eventProductRow.getDouble("price"))
                .addValue(eventProductRow.getString("category"));

        // Add user profile fields if available
        if (userProfile != null) {
            enrichedRowBuilder
                    .addValue(userProfile.getString("username"))
                    .addValue(userProfile.getString("user_segment"))
                    .addValue(userProfile.getString("registration_date"));
        } else {
            // Add null values if user profile not found
            enrichedRowBuilder
                    .addValue(null)
                    .addValue(null)
                    .addValue(null);
        }

        // Add processing timestamp
        enrichedRowBuilder.addValue(Instant.now());

        c.output(enrichedRowBuilder.build());
    }
}
