# atguigu/query_process/nodes/node_answer_output.py
import re

from config.model_prompt import ANSWER_PROMPT
from mj.query_process.base import NodeBase
from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from tool.get_model_tool import get_model_tool
from tool.mongo_tool import save_chat_message
from tool.task_utils import put_data


class NodeAnswerOutput(NodeBase):
    """
    节点功能: 答案生成
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_answer_output"

    def process(self, state: QueryGraphState):
        answer = state.get("answer")
        task_id = state.get("task_id")
        reranked_docs = state.get("reranked_docs")
        history_list = state.get("history")
        item_names = state.get("item_names")
        rewritten_query = state.get("rewritten_query")
        session_id = state.get("session_id")
        message_id = state.get("message_id")
        #
        if answer:
            #代表意图识别的时候就有答案了，只是还没推送给前端
            put_data(task_id=task_id,event="final",data={"answer":answer})
        else:
            #代表意图识别有确认的名字没有答案，接下来就得根据chunk让大模型生成答案，推送给前端
            # todo 整理chunks内容 context
            context = ""
            for item in reranked_docs:
                chunk_str = f"""
                    标题:{item.get("title")}\n
                    内容:{item.get("content")}\n
                    url:{item.get("url")}\n
                    来源:{item.get("source")}\n
                """
                context += chunk_str

            # todo 整理 history
            history = ""
            for item in history_list:
                history_str = f"{item.get("role")}:{item.get("text")}\n"
                history += history_str
            # todo 整理 item_names和question
            item_names_str = ",".join(item_names)
            question = rewritten_query

            # todo 提示词合并截断
            prompt = ANSWER_PROMPT.format(
                item_names=item_names_str,
                question=question,
                history=history,
                context=context,
            )[:10000]

            messages = [
                {"role":"user","content":prompt},
            ]

            llm = get_model_tool()

            res = llm.stream(messages) #生成器
            #大模型流式输出是一个生成器

            for item in res:
                #遍历生成器拿到每一小截答案，拿到了就存队列
                put_data(task_id=task_id,event="delta",data={"delta":item.content})
                answer += item.content #保存完整答案，后期历史记录当中需要保存

            # todo 推送完答案后的第一个善后处理
            #手动动chunks当中拿到图片，把这些图片的路径组成一个列表，单独推送给前端
            #1、保证回答的答案有图片就一定会给前端
            #2、为了让前端知道这个推送是最后的推送 final
            seen = set()  # 用于去重，避免同一张图片重复出现
            md_img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
            for i, doc in enumerate(reranked_docs):
                # 检查 text 字段中的 Markdown 图片 (主要针对 Local Chunk)
                text = doc.get("content")
                matches = md_img_pattern.findall(text)
                for img_url in matches:
                    img_url = img_url.strip()
                    seen.add(img_url)
            image_list = list(seen)
            put_data(task_id=task_id,event="final",data={"image_urls":image_list})


            # todo 推送完答案后的第二个善后处理 保存历史记录
            if answer:
                message_id = save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    text=answer,
                    rewritten_query=rewritten_query,
                    item_names=item_names,
                )
        return {
            "message_id": message_id,
        }


    # def process(self, state: QueryGraphState):
    #     """
    #     节点逻辑
    #     :param state: 工作流状态对象
    #     :return: 更新后的状态对象
    #     """
    #
    #     # TODO
    #     logger.info(f"【{self.name}】节点逻辑")
    #
    #     return state