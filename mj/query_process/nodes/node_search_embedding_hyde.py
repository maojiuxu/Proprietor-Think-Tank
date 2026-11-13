# atguigu/query_process/nodes/node_search_embedding_hyde.py
import json

from config.config import ConfigMilvus
from config.model_prompt import HYDE_PROMPT
from mj.query_process.base import NodeBase
from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from tool.bgem3_embedding_tool import get_bge3_embedding_vector
from tool.get_milvus_client import get_ann_search_req, get_hybrid_search_res
from tool.get_model_tool import get_model_tool
from tool.json_format_tool import json_format


class NodeSearchEmbeddingHyde(NodeBase):
    """
    节点功能：HyDE (Hypothetical Document Embedding)
    先让 LLM 生成假设性答案，再对答案进行向量检索，提高召回率。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_search_embedding_hyde"

    def process(self, state: QueryGraphState):
        item_names = state.get("item_names")
        rewritten_query = state.get("rewritten_query")

        llm = get_model_tool()
        prompt = [
            {"role": "user", "content": HYDE_PROMPT.format(rewritten_query=rewritten_query)}
        ]
        llm_res = llm.invoke(input=prompt)
        # print(llm_res.content)
        # 然后向量化这个大模型的结果，再将其与数据库中的数据做混合检索
        embeddings_res = get_bge3_embedding_vector([llm_res.content])
        dense = embeddings_res.get("dense")[0]
        sparse = embeddings_res.get("sparse")[0]

        expr = f"item_name in {json.dumps(item_names)}"
        reqs = get_ann_search_req(
            dense_vector=dense,
            sparse_vector=sparse,
            expr=expr
        )

        searched_res = get_hybrid_search_res(
            collection_name=ConfigMilvus.MILVUS_CHUNKS_COLLECTION_NAME,
            reqs=reqs,
            output_fields=["id", "section_content", "file_name", "section_title", "item_name"],
            ranker=(0.7, 0.3)
        )

        # print(json_format(searched_res[0]))

        chunks = [
            {
                **item.get("entity"),
                "score": item.get("distance"),
                "source": "local"
            }
            for item in searched_res[0]
        ]

        print(json_format(chunks))
        return {"hyde_embedding_chunks": chunks}

if __name__ == '__main__':
    node = NodeSearchEmbeddingHyde()
    init_state = {
        "item_names": ["RSPRORS-12数字万用表"],
        "rewritten_query": "万用表怎么使用"
    }
    node(init_state)