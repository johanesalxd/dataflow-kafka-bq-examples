package com.johanesalxd.transforms;

import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;
import org.apache.beam.sdk.values.Row;
import org.joda.time.Instant;

/**
 * DoFn to deduplicate user profiles by keeping only the latest record per user_id.
 * This handles the case where BigQuery table contains multiple entries for the same user.
 */
public class DeduplicateUserProfilesDoFn extends DoFn<KV<String, Iterable<Row>>, KV<String, Row>> {

    @ProcessElement
    public void processElement(ProcessContext c) {
        KV<String, Iterable<Row>> element = c.element();
        String userId = element.getKey();
        Iterable<Row> userProfiles = element.getValue();

        Row latestProfile = null;
        Instant latestTimestamp = null;

        // Find the profile with the latest timestamp
        for (Row profile : userProfiles) {
            Instant profileTimestamp = profile.getDateTime("timestamp").toInstant();

            if (latestProfile == null ||
                (profileTimestamp != null &&
                 (latestTimestamp == null || profileTimestamp.isAfter(latestTimestamp)))) {
                latestProfile = profile;
                latestTimestamp = profileTimestamp;
            }
        }

        // Output the latest profile for this user_id
        if (latestProfile != null) {
            c.output(KV.of(userId, latestProfile));
        }
    }
}
