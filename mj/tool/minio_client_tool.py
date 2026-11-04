"""
本文档用来创建minio的单例
"""
import json

from minio import Minio

from mj.config.config import ConfigMinio

minio_client = None

def get_minio_client():
    global minio_client

    if minio_client is None:
        # 首先创建连接
        minio_client = Minio(
            endpoint=ConfigMinio.MINIO_ENDPOINT,
            access_key=ConfigMinio.MINIO_ACCESS_KEY,
            secret_key=ConfigMinio.MINIO_SECRET_KEY,
            secure=False # 这个必须写上，不然后面会报错
        )

        bucket_name = ConfigMinio.MINIO_BUCKET_NAME

        # 然后创建一个bucket
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name=bucket_name)

        # 更改这个bucket的权限为只读权限：从官网上的github上找示例
        # Example anonymous read-only bucket policy.
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": f"arn:aws:s3:::{bucket_name}",
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                },
            ],
        }
        minio_client.set_bucket_policy(bucket_name=bucket_name, policy=json.dumps(policy))

    return minio_client

# if __name__ == '__main__':
#     minio_client = get_minio_client()