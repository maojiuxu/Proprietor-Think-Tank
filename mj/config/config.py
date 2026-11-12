# 该文件用来加载.env文件中的key等信息
import os

from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path=env_path, override=True)


class ConfigMineru:
    mineru_token = os.getenv("MINERU_TOKEN")

class ConfigVLM:
    V_MODEL_NAME = os.getenv("V_MODEL_NAME")
    V_MODEL_BASE_URL = os.getenv("MODEL_DEFAULT_BASE_URL")
    V_MODEL_API_KEY = os.getenv("MODEL_DEFAULT_API_KEY")
    V_MODEL_TEMPERATURE = float(os.getenv("MODEL_DEFAULT_TEMPERATURE"))
    MODEL_DEFAULT_NAME = os.getenv("MODEL_DEFAULT_NAME")
    MODEL_NAME_37_PLUS = os.getenv("MODEL_NAME_37_PLUS")

class ConfigMinio:
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")
    MINIO_BUCKET_DIR = os.getenv("MINIO_BUCKET_DIR")

class BGEM3Config:
    BGE_M3_PATH = os.getenv("BGE_M3_PATH")
    BGE_M3 = os.getenv("BGE_M3")
    BGE_DEVICE = os.getenv("BGE_DEVICE")
    BGE_FP16 = os.getenv("BGE_FP16") in ("True", "TRUE", "true", "1", "on")

class ConfigMilvus:
    MILVUS_URL = os.getenv("MILVUS_URL")
    MILVUS_NAME = os.getenv("MILVUS_NAME")
    MILVUS_CHUNKS_COLLECTION_NAME = os.getenv("MILVUS_CHUNKS_COLLECTION_NAME")

class ConfigMongo:
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
    MONGO_URL = os.getenv("MONGO_URL")
