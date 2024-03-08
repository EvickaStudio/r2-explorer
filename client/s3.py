import json
from typing import Dict, List

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, NoCredentialsError


class S3Client:
    def __init__(self, config_file: str) -> None:
        """
        Initialize the S3 client with the given configuration file.

        :param config_file: The path to the configuration file.
        """
        try:
            with open(config_file) as json_file:
                config = json.load(json_file)

            AccountID = config["ACCOUNT_ID"]
            ClientAccessKey = config["CLIENT_ACCESS_KEY"]
            ClientSecret = config["CLIENT_SECRET"]

            ConnectionUrl = f"https://{AccountID}.r2.cloudflarestorage.com"

            self.client = boto3.client(
                "s3",
                endpoint_url=ConnectionUrl,
                aws_access_key_id=ClientAccessKey,
                aws_secret_access_key=ClientSecret,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        except (FileNotFoundError, KeyError) as e:
            print(f"Failed to initialize S3 client: {e}")
            raise

    def list_buckets_names(self) -> List[str]:
        """
        List the names of all buckets.

        :return: A list of bucket names.
        """
        try:
            response = self.client.list_buckets()
            return [bucket["Name"] for bucket in response["Buckets"]]
        except (BotoCoreError, NoCredentialsError) as e:
            print(f"Failed to list bucket names: {e}")
            raise

    def list_objects(self, bucket: str) -> List[Dict[str, str]]:
        """
        List all objects in a bucket.

        :param bucket: The name of the bucket.
        :return: A list of objects in the bucket.
        """
        try:
            response = self.client.list_objects(Bucket=bucket)
            return response.get("Contents", [])
        except (BotoCoreError, NoCredentialsError) as e:
            print(f"Failed to list objects in bucket '{bucket}': {e}")
            raise

    def generate_url(self, bucket: str, item: str) -> str:
        """
        Generate a presigned URL for an object.

        :param bucket: The name of the bucket.
        :param item: The name of the object.
        :return: A presigned URL for the object.
        """
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": item},
                ExpiresIn=3600,
            )
        except (BotoCoreError, NoCredentialsError) as e:
            print(
                f"Failed to generate URL for object '{item}' in bucket '{bucket}': {e}"
            )
            raise

    def delete(self, bucket: str, item: str) -> None:
        """
        Delete an object.

        :param bucket: The name of the bucket.
        :param item: The name of the object.
        """
        try:
            self.client.delete_object(Bucket=bucket, Key=item)
        except (BotoCoreError, NoCredentialsError) as e:
            print(f"Failed to delete object '{item}' in bucket '{bucket}': {e}")
            raise

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        """
        Download a file.

        :param bucket: The name of the bucket.
        :param key: The key of the object.
        :param filename: The name of the file to download to.
        """
        try:
            self.client.download_file(bucket, key, filename)
        except (BotoCoreError, NoCredentialsError) as e:
            print(f"Failed to download file '{key}' from bucket '{bucket}': {e}")
            raise

    def upload_file(self, bucket: str, key: str, filename: str) -> None:
        """
        Upload a file.

        :param bucket: The name of the bucket.
        :param key: The key of the object.
        :param filename: The name of the file to upload.
        """
        try:
            self.client.upload_file(filename, bucket, key)
        except (BotoCoreError, NoCredentialsError) as e:
            print(f"Failed to upload file '{filename}' to bucket '{bucket}': {e}")
            raise

    def show_storage_usage(self) -> Dict[str, int]:
        """
        Show the storage usage of all buckets.

        :return: A dictionary with the storage usage of all buckets.
        """
        try:
            response = self.client.list_buckets()
            return {
                bucket["Name"]: sum(
                    obj["Size"]
                    for obj in self.client.list_objects(Bucket=bucket["Name"]).get(
                        "Contents", []
                    )
                )
                for bucket in response["Buckets"]
            }
        except (BotoCoreError, NoCredentialsError) as e:
            print(f"Failed to show storage usage: {e}")
            raise
