# This script calculates the total storage usage (in MB) across all buckets.
# It's particularly useful for monitoring usage when operating within the R2 free tier, helping to avoid exceeding the limit.

from typing import Dict

from client.s3 import S3Client

s3_client: S3Client = S3Client("config.json")


def calculate_storage_usage(buckets: Dict[str, int]) -> int:
    return sum(round(bucket_size / 1024 / 1024, 2) for bucket_size in buckets.values())


print(f"{calculate_storage_usage(s3_client.show_storage_usage())} MB")
