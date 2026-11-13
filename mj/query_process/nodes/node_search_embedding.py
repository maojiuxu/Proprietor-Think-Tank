# atguigu/query_process/nodes/node_search_embedding.py
import json

from config.config import ConfigMilvus
from mj.query_process.base import NodeBase
from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from tool.bgem3_embedding_tool import get_bge3_embedding_vector
from tool.get_milvus_client import get_ann_search_req, get_hybrid_search_res
from rich import print as rprint

from tool.json_format_tool import json_format


class NodeSearchEmbedding(NodeBase):
    """
    节点功能：基于已确认主体名+改写后的用户问题，执行Milvus向量数据库混合检索
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_search_embedding"

    def process(self, state: QueryGraphState):
        item_names = state.get("item_names")
        rewritten_query = state.get("rewritten_query")

        # 获取重写问题的稠密和稀疏向量
        rewritten_query_res = get_bge3_embedding_vector([rewritten_query])
        rewritten_query_dense = rewritten_query_res.get("dense")[0]
        rewritten_query_sparse = rewritten_query_res.get("sparse")[0]

        # 根据向量对数据库进行混合检索得到chunks
        expr = f"item_name in {json.dumps(item_names)}"
        reqs = get_ann_search_req(
            dense_vector=rewritten_query_dense,
            sparse_vector=rewritten_query_sparse,
            limit=10,
            expr=expr
        )

        hybrid_search_list = get_hybrid_search_res(
            collection_name=ConfigMilvus.MILVUS_CHUNKS_COLLECTION_NAME,
            reqs=reqs,
            output_fields=["id", "section_content", "item_name", "section_title","file_name"],
            ranker=(0.8, 0.2)
        )
        # rprint(hybrid_search_list[0])
        chunks = [
            {
                **item.get("entity"),
                "score": item.get("distance"),
                "source": "local"
            }
            for item in hybrid_search_list[0]
        ]
        print(json_format(chunks))

        return {"embedding_chunks":  chunks}


if __name__ == '__main__':
    node = NodeSearchEmbedding()
    init_state = {
        "item_names": ["RSPRORS-12数字万用表"],
        "rewritten_query": "万用表怎么使用"
    }
    node(init_state)