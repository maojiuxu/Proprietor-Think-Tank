# 该文件用来加载.env文件中的key等信息
import os

from dotenv import load_dotenv
load_dotenv()


class ConfigMineru:
    mineru_token = os.getenv("MINERU_TOKEN")