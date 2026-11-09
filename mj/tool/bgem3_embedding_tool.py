from typing import List
from rich import print as rprint

from pymilvus.model.hybrid import BGEM3EmbeddingFunction

from mj.config.config import BGEM3Config
from mj.tool.json_format_tool import json_format

# 模型单例
bgem3_embedding_model = None

# 获取模型实例
def get_bgem3_embedding_model():
    global bgem3_embedding_model
    if bgem3_embedding_model is None:
        bgem3_embedding_model = BGEM3EmbeddingFunction(
            model_name=BGEM3Config.BGE_M3_PATH,
            devices=BGEM3Config.BGE_DEVICE,
            use_fp16=BGEM3Config.BGE_FP16
        )
    return bgem3_embedding_model

# 使用BGEM3模型去对切分好的列表做嵌入
def get_bge3_embedding_vector(documents: List[str]):
    model = get_bgem3_embedding_model()
    res = model.encode_documents(documents)

    # 返回稀疏和稠密向量
    return {
        "dense": [item.tolist() for item in res.get('dense')],
        "sparse": [dict(zip(item.indices.tolist(), item.data.tolist())) for item in res.get('sparse')]
    }


if __name__ == '__main__':
    init_documents = ["动手学深度学习", "迭代器、上下文管理器、asyncio"]
    get_bge3_embedding_vector(init_documents)
