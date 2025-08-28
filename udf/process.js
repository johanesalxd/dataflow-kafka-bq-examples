/**
 * A User-Defined Function (UDF) for a Dataflow template that processes a JSON message from Kafka.
 *
 * This function takes a JSON string payload, extracts an event timestamp, adds a
 * processing timestamp, and returns a new JSON string formatted for a BigQuery table.
 *
 * @param {string} payload The raw message payload from Kafka, expected to be a JSON string.
 * @returns {string} A new JSON string with event_time, processing_time, and the original payload.
 */
function process(payload) {
  // Parse the incoming JSON string into an object
  const data = JSON.parse(payload);

  // --- IMPORTANT ---
  // Access the event timestamp from your message.
  // Modify 'data.timestamp' to match the actual key in your JSON payload.
  // For example, if your timestamp is in a field called 'createdAt', use 'data.createdAt'.
  const eventTime = data.timestamp;

  // Create a new object that matches the BigQuery schema
  const outputRecord = {
    event_time: eventTime,
    processing_time: new Date().toISOString(), // Current time in UTC ISO format
    payload: payload // The original, unmodified JSON payload as a string
  };

  // Return the new object as a string
  return JSON.stringify(outputRecord);
}
