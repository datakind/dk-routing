import os

import boto3

def get_client():
    """Will need proper credential management, probably"""
    
    client = boto3.client(
        's3',
        aws_access_key_id=os.environ["AWSACCESSKEYID"],
        aws_secret_access_key=os.environ["AWSSECRETACCESSKEY"])
    
    return client