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

