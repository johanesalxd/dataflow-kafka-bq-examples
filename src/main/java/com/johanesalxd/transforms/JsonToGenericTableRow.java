package com.johanesalxd.transforms;

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;
import org.json.JSONObject;

import java.time.Instant;

public class JsonToGenericTableRow extends DoFn<KV<String, String>, TableRow> {

    @ProcessElement
    public void processElement(ProcessContext c) {
        String json = c.element().getValue();
        JSONObject jsonObject = new JSONObject(json);

        TableRow row = new TableRow();

        // Extract event timestamp from the JSON payload
        row.set("event_time", jsonObject.getString("timestamp"));

        // Add current processing timestamp
        row.set("processing_time", Instant.now().toString());

        // Store the full JSON payload as-is
        row.set("payload", json);

        c.output(row);
    }
}
