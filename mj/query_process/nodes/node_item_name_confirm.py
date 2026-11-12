# atguigu/query_process/nodes/node_item_name_confirm.py

import json

from config.config import ConfigVLM, ConfigMilvus
from config.model_prompt import ITEM_NAME_EXTRACT_SYSTEM_PROMPT, ITEM_NAME_EXTRACT_TEMPLATE
from mj.query_process.base import NodeBase
from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from tool.bgem3_embedding_tool import bgem3_embedding_model, get_bge3_embedding_vector
from tool.get_milvus_client import get_ann_search_req, get_hybrid_search_res
from tool.get_model_tool import get_model_tool
from tool.mongo_tool import get_recent_messages, save_chat_message, update_history_item_names
from rich import print as rprint


class NodeItemNameConfirm(NodeBase):
    """
    节点功能：确认用户问题中的核心商品名称。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_item_name_confirm"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """
        original_query = state.get("original_query")
        session_id = state.get("session_id")

        if not original_query:
            logger.error("原始问题不能为空")
            raise Exception("原始问题不能为空")
        if not session_id:
            logger.error("当前会话id不能为空")
            raise Exception("当前会话id不能为空")

        # 一、想要获取用户的意图，需要将最近十条的数据拿到，然后一并打包给大模型
        history_message_list = get_recent_messages(session_id=session_id)
        message_id = save_chat_message(session_id=session_id, role="user", text=original_query)
        history_str = ""
        for history_message in history_message_list:
            history_str += f"{history_message.get("role")}:{history_message.get("text")}\n\n"
            # history_str += f"角色:{history_message.get("role")}\n内容:{history_message.get("text")}\n\n"
        # llm = get_model_tool(model_name=ConfigVLM.MODEL_NAME_37_PLUS)
        llm = get_model_tool()
        prompt = [
            {"role": "system", "content": ITEM_NAME_EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": ITEM_NAME_EXTRACT_TEMPLATE.format(history_text=history_str, original_query=original_query)}
        ]

        res = llm.invoke(input=prompt)
        # rprint(history_message_list)
        # rprint(history_str)
        print("--------------------------------------------")
        rprint(f"原始问题：{original_query}")
        rprint(res.content)

        # 对大模型返回的JSON串进行处理并转为字典格式，最后通过字典的.get()方法去拿到大模型识别到的item_names
        dict_content = json.loads(res.content.replace("```json", "").replace("```", ""))
        intention_item_names = [ item_name.replace("\n", "").replace("\t","").replace(" ","") for item_name in dict_content.get("item_names", []) ]
        rewritten_query = dict_content.get("rewritten_query", original_query)

        # 二、现在需要将大模型识别到的item_names与milvus中主体识别的表格做相似度检索，然后得到一组数据
        if intention_item_names:
            # 当意图不为空时：
            # 2.1 首先将得到的意图向量化得到稀疏和稠密向量
            intention_embeddings = get_bge3_embedding_vector(intention_item_names)
            # 拿到向量后，做相似度混合检索
            search_results = []
            for idx,intention_item_name in enumerate(intention_item_names):
                dense = intention_embeddings.get("dense")[idx]
                sparse = intention_embeddings.get("sparse")[idx]
                reqs = get_ann_search_req(dense_vector=dense, sparse_vector=sparse)
                search_res = get_hybrid_search_res(
                    collection_name=ConfigMilvus.MILVUS_NAME,
                    reqs=reqs,
                    output_fields=["item_name", "file_title"],
                    ranker=(0.8, 0.2)
                )
                # print("====================================")
                # rprint(search_res[0])
                for searched_item in search_res[0]:
                    search_results.append({
                        # "id": searched_item.get("id"),
                        "score": searched_item.get("distance"),
                        "item_name": searched_item.get("entity").get("item_name"),
                        "orginal_item_name": intention_item_name
                    })
            print("数据库中混合检索查询到的结果：================================")
            rprint(search_results)
            # 现在已经拿到结果了，需要把结果对齐
            answer = ""
            final_item_names = []
            confirm_item_name = [search_result.get("item_name") for search_result in search_results if search_result.get("score") > 0.8 ]
            option_item_names = [
                search_result.get("item_name")
                for search_result in search_results
                if search_result.get("score") < 0.8 and search_result.get("score") > 0.6
            ]
            if confirm_item_name:
                answer = ""
                final_item_names = confirm_item_name
            elif option_item_names:
                answer = f"请问您要咨询的商品名字是哪一个：{','.join(option_item_names)}"
                final_item_names = []
            else:
                final_item_names = []
                answer = "不好意思，没有识别到您问的商品，请重新提问"

            if answer:
                message_id = save_chat_message(session_id, "assistant", answer)
            # 不管有没有新记录，都要把识别到的最终确认的的final_item_names和重写的问题，回填给历史记录
            history_list = get_recent_messages(session_id)
            ids = [item.get("_id") for item in history_list]
            if ids:
                update_history_item_names(ids, item_names=final_item_names, rewritten_query=rewritten_query)

        return {
            "original_query": original_query,
            "answer": answer,
            "item_names": final_item_names,
            "rewritten_query": rewritten_query,
            "history": get_recent_messages(session_id),  # 一定要最终重新从mongo获取一次最近修改后的历史记录
            "session_id": session_id
        }

if __name__ == '__main__':
    node = NodeItemNameConfirm()
    init_state = {
        "original_query": "万用表",
        "session_id": "test_001"
    }
    node(init_state)


