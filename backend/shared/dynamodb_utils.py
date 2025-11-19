import os
from functools import lru_cache

import boto3
from botocore.config import Config


def _aws_region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS-REGION") or "us-east-1"


@lru_cache(maxsize=1)
def get_resource():
    return boto3.resource(
        "dynamodb",
        region_name=_aws_region(),
        config=Config(retries={"mode": "standard", "max_attempts": 5}),
    )


def get_table(table_name: str):
    if not table_name:
        raise ValueError("table_name is required")
    return get_resource().Table(table_name)