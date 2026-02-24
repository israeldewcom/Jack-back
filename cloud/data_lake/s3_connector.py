import boto3
import pandas as pd
from io import StringIO
import os

class S3Connector:
    def __init__(self, bucket: str):
        self.s3 = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
        )
        self.bucket = bucket

    def upload_features(self, org_id: str, date: str, features_df: pd.DataFrame):
        csv_buffer = StringIO()
        features_df.to_csv(csv_buffer, index=False)
        key = f"features/{org_id}/{date}/features.csv"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=csv_buffer.getvalue())
        return key

    def download_features(self, org_id: str, date: str) -> pd.DataFrame:
        key = f"features/{org_id}/{date}/features.csv"
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        return pd.read_csv(obj['Body'])
