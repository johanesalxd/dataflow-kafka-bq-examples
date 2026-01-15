"""Custom pipeline options for Pub/Sub to BigQuery pipeline."""

from apache_beam.options.pipeline_options import PipelineOptions


class PubSubToBigQueryOptions(PipelineOptions):
    """Custom pipeline options for the Pub/Sub to BigQuery pipeline.

    These options define the configuration parameters for reading from Pub/Sub
    and writing to BigQuery.
    """

    @classmethod
    def _add_argparse_args(cls, parser):
        """Adds custom command-line arguments to the parser.

        Args:
            parser: ArgumentParser object to add arguments to.
        """
        parser.add_argument(
            '--subscription',
            required=True,
            help='Pub/Sub subscription name (e.g., projects/PROJECT_ID/subscriptions/SUBSCRIPTION_NAME)',
        )
        parser.add_argument(
            '--output_table',
            required=True,
            help='BigQuery output table (e.g., PROJECT_ID:DATASET.TABLE)',
        )
        parser.add_argument(
            '--subscription_name',
            required=False,
            default='taxi_telemetry',
            help='Subscription name to record in BigQuery (default: taxi_telemetry)',
        )
