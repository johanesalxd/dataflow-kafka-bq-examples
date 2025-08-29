SELECT
    ue.event_id,
    ue.user_id,
    ue.event_type,
    ue.event_time as event_timestamp,
    pu.product_id,
    pu.product_name,
    pu.price,
    pu.category
FROM user_events ue
LEFT JOIN product_updates pu ON ue.product_id = pu.product_id
