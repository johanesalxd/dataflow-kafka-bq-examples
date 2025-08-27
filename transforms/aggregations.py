"""Aggregation transforms using Beam SQL."""

import logging
from typing import Any, Dict

import apache_beam as beam
from apache_beam.transforms import window
from apache_beam.transforms.sql import SqlTransform


class WindowedAggregation(beam.PTransform):
    """Apply windowing and SQL aggregation to messages."""

    def __init__(self, window_duration: int, sql_query: str, table_name: str):
        """
        Initialize windowed aggregation transform.

        Args:
            window_duration: Window duration in seconds
            sql_query: SQL query for aggregation
            table_name: Name for the SQL table
        """
        self.window_duration = window_duration
        self.sql_query = sql_query
        self.table_name = table_name

    def expand(self, pcoll):
        """
        Apply windowing and SQL aggregation.

        Args:
            pcoll: Input PCollection

        Returns:
            Aggregated PCollection
        """
        return (
            pcoll
            | f'Window_{self.table_name}' >> beam.WindowInto(
                window.FixedWindows(self.window_duration)
            )
            | f'SQL_Aggregate_{self.table_name}' >> SqlTransform(
                self.sql_query,
                dialect='zetasql'
            )
        )


def get_user_events_aggregation_query() -> str:
    """Get SQL query for user events aggregation."""
    return """
    SELECT
        user_id,
        COUNT(*) as event_count,
        COUNT(DISTINCT event_type) as unique_event_types,
        COUNT(DISTINCT product_id) as unique_products,
        MIN(timestamp) as window_start_time,
        MAX(timestamp) as window_end_time,
        CURRENT_TIMESTAMP() as aggregation_time
    FROM PCOLLECTION
    GROUP BY user_id
    """


def get_product_updates_aggregation_query() -> str:
    """Get SQL query for product updates aggregation."""
    return """
    SELECT
        product_id,
        COUNT(*) as update_count,
        AVG(price) as avg_price,
        MIN(price) as min_price,
        MAX(price) as max_price,
        category,
        MIN(timestamp) as window_start_time,
        MAX(timestamp) as window_end_time,
        CURRENT_TIMESTAMP() as aggregation_time
    FROM PCOLLECTION
    GROUP BY product_id, category
    """


def get_user_profiles_aggregation_query() -> str:
    """Get SQL query for user profiles aggregation."""
    return """
    SELECT
        user_segment,
        COUNT(*) as profile_count,
        COUNT(DISTINCT user_id) as unique_users,
        MIN(timestamp) as window_start_time,
        MAX(timestamp) as window_end_time,
        CURRENT_TIMESTAMP() as aggregation_time
    FROM PCOLLECTION
    GROUP BY user_segment
    """


class PrepareForBigQuery(beam.DoFn):
    """Prepare aggregated data for BigQuery insertion."""

    def process(self, element):
        """
        Convert aggregated data to BigQuery-compatible format.

        Args:
            element: Aggregated data dictionary

        Yields:
            BigQuery-compatible record
        """
        try:
            # Ensure all timestamp fields are properly formatted
            if 'window_start_time' in element and element['window_start_time']:
                element['window_start_time'] = str(
                    element['window_start_time'])

            if 'window_end_time' in element and element['window_end_time']:
                element['window_end_time'] = str(element['window_end_time'])

            if 'aggregation_time' in element and element['aggregation_time']:
                element['aggregation_time'] = str(element['aggregation_time'])

            # Convert any None values to appropriate defaults
            for key, value in element.items():
                if value is None:
                    if key.endswith('_count') or key.endswith('_price'):
                        element[key] = 0
                    elif key.endswith('_time'):
                        # Keep as None for timestamp fields
                        element[key] = None
                    else:
                        element[key] = ''

            yield element

        except Exception as e:
            logging.error(f"Error preparing data for BigQuery: {e}")
            # Send to DLQ
            yield beam.pvalue.TaggedOutput('dlq', {
                'original_data': element,
                'error': f"BigQuery preparation error: {str(e)}",
                'processing_time': beam.utils.timestamp.Timestamp.now().to_utc_datetime().isoformat()
            })


def create_aggregation_pipeline(topic_config: Dict[str, Any], window_duration: int):
    """
    Create aggregation pipeline for a specific topic.

    Args:
        topic_config: Topic configuration dictionary
        window_duration: Window duration in seconds

    Returns:
        Tuple of (aggregation_transform, sql_query)
    """
    topic_name = topic_config['name']

    # Select appropriate SQL query based on topic
    if topic_name == 'user-events':
        sql_query = get_user_events_aggregation_query()
    elif topic_name == 'product-updates':
        sql_query = get_product_updates_aggregation_query()
    elif topic_name == 'user-profiles':
        sql_query = get_user_profiles_aggregation_query()
    else:
        raise ValueError(f"Unknown topic for aggregation: {topic_name}")

    aggregation_transform = WindowedAggregation(
        window_duration=window_duration,
        sql_query=sql_query,
        table_name=topic_name.replace('-', '_')
    )

    return aggregation_transform, sql_query
