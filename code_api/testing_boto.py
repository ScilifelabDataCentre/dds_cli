import boto3
import os
from pathlib import Path
import json

path = Path(os.getcwd()).parent
print(f"{path}/s3_config.json")

with open(f"{path}/s3_config.json") as f:
    data = json.load(f)

access_key = data['access_key']
secret_key = data['secret_key']
endpoint_url = data['endpoint_url']

s3 = boto3.resource(
	service_name='s3', 
	endpoint_url = endpoint_url,
	aws_access_key_id = access_key,
	aws_secret_access_key = secret_key,
)

for bucket in s3.buckets.all():
	print(bucket.name)
