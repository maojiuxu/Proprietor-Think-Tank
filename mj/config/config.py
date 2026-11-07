# 该文件用来加载.env文件中的key等信息
import os

from dotenv import load_dotenv
load_dotenv()


class ConfigMineru:
    mineru_token = os.getenv("MINERU_TOKEN")

class ConfigVLM:
    V_MODEL_NAME = os.getenv("V_MODEL_NAME")
    V_MODEL_BASE_URL = os.getenv("V_MODEL_BASE_URL")
    V_MODEL_API_KEY = os.getenv("V_MODEL_API_KEY")
    V_MODEL_TEMPERATURE = float(os.getenv("V_MODEL_TEMPERATURE"))

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