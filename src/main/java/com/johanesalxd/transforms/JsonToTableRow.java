package com.johanesalxd.transforms;

import com.google.api.services.bigquery.model.TableRow;
import org.apache.beam.sdk.transforms.DoFn;
import org.apache.beam.sdk.values.KV;
import org.json.JSONObject;

import java.time.Instant;

public class JsonToTableRow extends DoFn<KV<String, String>, TableRow> {

    @ProcessElement
    public void processElement(ProcessContext c) {
        String json = c.element().getValue();
        JSONObject jsonObject = new JSONObject(json);
        TableRow row = new TableRow();
        row.set("event_id", jsonObject.getString("event_id"));
        row.set("user_id", jsonObject.getString("user_id"));
        row.set("event_type", jsonObject.getString("event_type"));
        row.set("product_id", jsonObject.optString("product_id"));
        row.set("timestamp", jsonObject.getString("timestamp"));
        row.set("processing_time", Instant.now().toString());
        c.output(row);
    }
}
