from pymilvus import MilvusClient

from mj.config.config import ConfigMilvus

milvus_client = None

def get_milvus_client():
    global milvus_client
    if milvus_client is None:
        milvus_client = MilvusClient(
            uri=ConfigMilvus.MILVUS_URL
        )
    return milvus_client