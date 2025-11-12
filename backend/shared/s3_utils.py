#s3 util functions for RAG
# functions: handles urls, file uploads, downloads, bucket ops

from http import HTTPMethod
import boto3
from botocore.config import Config
import json
import os
from typing import Any, Optional, Dict

# creates s3 client
# centralizes client creation
# no need to issue new creds on each call
def get_s3_client():
    return boto3.client('s3', region_name=os.environ.get('AWS-REGION', 'us-east-1'),
                        config=Config(signature_version="s3v4"),)

# returns time limited s3 put url for uploads
# 900s default time, returns url, headers, key
def generate_put_url(bucket: str, key: str, expiration: int = 900):
    s3_client = get_s3_client()
    
    try:
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration,
            HttpMethod="PUT",
        )
        
        return {
            'url': url,
            'putHeaders': {
                'Content-Type': 'application/octet-stream'
            },
            'key': key
        }
    except Exception as e:
        print(f"error generating URL: {e}")
        raise

# downloads s3 object to local temp storage
# for ingest and query lambdas to access files
# lmabda runs in containers, so we download to local
def download_object(bucket: str, key: str, local_path: str):
    s3_client = get_s3_client()
    
    try:
        s3_client.download_file(bucket, key, local_path)
        return local_path
    except Exception as e:
        print(f"error downloading from s3: {e}")
        raise

# upload local file to s3
# for writing generated indexes (FAISS)
def upload_file(local_path: str, bucket: str, key: str):
    s3_client = get_s3_client()
    
    try:
        s3_client.upload_file(local_path, bucket, key)
        return key
    except Exception as e:
        print(f"error uploading to s3: {e}")

# list objects under a prefix
# for ingest lmambda to discover uploaded files
def list_objects(bucket: str, prefix: str):
    s3_client = get_s3_client()
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        return []
    except Exception as e:
        print(f"error listing s3 objects: {e}")
        raise

# checks if object in s3 without downloading
# to verify and check for indexes
def if_object(bucket: str, key: str):
    s3_client = get_s3_client()
    
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise

# returns the ETag for an S3 object so callers can detect updates
def get_etag(bucket: str, key: str):
    s3_client = get_s3_client()

    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return response.get('ETag')
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        raise