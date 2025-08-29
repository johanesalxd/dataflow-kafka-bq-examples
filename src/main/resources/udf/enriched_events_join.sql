SELECT
    ue.event_id,
    ue.user_id,
    ue.event_type,
    ue.event_time as event_timestamp,
    pu.product_id,
    pu.product_name,
    pu.price,
    pu.category,
    up.username,
    up.user_segment,
    up.registration_date
FROM user_events ue
LEFT JOIN product_updates pu ON ue.product_id = pu.product_id
LEFT JOIN user_profiles up ON ue.user_id = up.user_id
