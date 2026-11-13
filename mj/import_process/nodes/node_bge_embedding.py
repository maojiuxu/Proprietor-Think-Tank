import json

from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.bgem3_embedding_tool import get_bge3_embedding_vector
from mj.tool.json_format_tool import json_format
from mj.tool.logger import logger
from rich import print as rprint


class NodeBGEEmbedding(NodeBase):
    """
    混合向量化
    """
    name = "node_bge_embedding"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑
        chunks = state.get("chunks")
        if not chunks:
            logger.error("chunks不存在")
            raise Exception("chunks不存在")


        # step = 5
        # for idx in range(0, len(chunks), step):
        #     chunk_str_list = chunks[idx: idx + step]
        #     res = get_bge3_embedding_vector([f"{chunk.get('item_name')}{chunk.get('content')}" for chunk in chunk_str_list])
        #     for idx_inner, chunk in enumerate(chunk_str_list):
        #         chunk["dense_vector"] = res.get("dense")[idx_inner]
        #         chunk["sparse_vector"] = res.get("sparse")[idx_inner]

        res = get_bge3_embedding_vector(
            [f"{chunk.get('item_name')}{chunk.get('section_content')}" for chunk in chunks]
        )

        print(json_format(res))

        for idx,chunk in enumerate(chunks):
            chunk["dense_vector"] = res.get("dense")[idx]
            chunk["sparse_vector"] = res.get("sparse")[idx]

        # rprint(chunks)
        # with open(r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\json\bgem3_embedding_chunks.json", "w", encoding="utf-8") as f:
        #     f.write(json_format(chunks))

        # 拿到从嵌入模型得到的稠密和稀疏向量并保存到chunks中
        return {
            "chunks": chunks
        }


# 此处进行单元测试
if __name__ == "__main__":
    node = NodeBGEEmbedding()
    with open(r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\json\item_name_chunks.json", "r", encoding="utf-8") as f:
        chunks_state = json.load(f)
    init_state = {
        "chunks": chunks_state
    }
    node(init_state)