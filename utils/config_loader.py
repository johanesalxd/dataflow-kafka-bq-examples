"""Configuration loader for the Dataflow pipeline."""

import logging
from typing import Any, Dict

import yaml


def load_config(config_path: str, environment: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file for the specified environment.

    Args:
        config_path: Path to the configuration YAML file
        environment: Environment name (local, cloud)

    Returns:
        Configuration dictionary for the specified environment

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If environment not found in config
        yaml.YAMLError: If YAML parsing fails
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        if environment not in config:
            raise KeyError(
                f"Environment '{environment}' not found in config. Available: {list(config.keys())}")

        env_config = config[environment]
        logging.info(f"Loaded configuration for environment: {environment}")

        return env_config

    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        raise


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate that required configuration keys are present.

    Args:
        config: Configuration dictionary

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If required keys are missing
    """
    required_keys = [
        'runner',
        'kafka',
        'bigquery',
        'pipeline'
    ]

    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(
            f"Missing required configuration keys: {missing_keys}")

    # Validate Kafka configuration
    kafka_required = ['bootstrap_servers', 'topics']
    kafka_missing = [
        key for key in kafka_required if key not in config['kafka']]
    if kafka_missing:
        raise ValueError(
            f"Missing required Kafka configuration keys: {kafka_missing}")

    # Validate BigQuery configuration
    bq_required = ['project_id', 'dataset']
    bq_missing = [key for key in bq_required if key not in config['bigquery']]
    if bq_missing:
        raise ValueError(
            f"Missing required BigQuery configuration keys: {bq_missing}")

    logging.info("Configuration validation passed")
    return True


def get_table_spec(config: Dict[str, Any], table_name: str) -> str:
    """
    Generate BigQuery table specification string.

    Args:
        config: Configuration dictionary
        table_name: Name of the table

    Returns:
        BigQuery table specification in format: project:dataset.table
    """
    project_id = config['bigquery']['project_id']
    dataset = config['bigquery']['dataset']
    return f"{project_id}:{dataset}.{table_name}"
