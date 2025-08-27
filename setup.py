"""
Setup file for Dataflow Kafka to BigQuery pipeline.
Required for DataflowRunner deployment.
"""

import setuptools

# Read requirements from requirements.txt
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip()
                    and not line.startswith("#")]

setuptools.setup(
    name="dataflow-kafka-bq-examples",
    version="1.0.0",
    author="Dataflow Demo",
    author_email="demo@example.com",
    description="Dataflow pipeline for streaming Kafka data to BigQuery",
    long_description="A demonstration pipeline that reads from Kafka topics and writes to BigQuery with branching for raw and aggregated data.",
    long_description_content_type="text/plain",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
