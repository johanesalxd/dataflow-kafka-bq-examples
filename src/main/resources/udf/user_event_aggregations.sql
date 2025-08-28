SELECT
  event_type,
  COUNT(*) as event_count,
  TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
  TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end
FROM PCOLLECTION
GROUP BY
  event_type,
  TUMBLE(event_time, INTERVAL '1' MINUTE)
