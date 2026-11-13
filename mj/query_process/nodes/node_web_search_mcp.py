# atguigu/query_process/nodes/node_web_search_mcp.py
import json

from agents.mcp import MCPServerStreamableHttp

from config.config import ConfigMCP
from mj.query_process.base import NodeBase
from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from tool.json_format_tool import json_format
from rich import print as rprint


class NodeWebSearchMcp(NodeBase):
    """
    节点功能，调用外部搜索引擎补充信息
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_web_search_mcp"

    def process(self, state: QueryGraphState):
        """
        节点逻辑
        :param state: 工作流状态对象
        :return: 更新后的状态对象
        """
        rewritten_query = state.get("rewritten_query")
        if not rewritten_query:
            logger.error("rewritten_query不能为空")
            raise ValueError("rewritten_query不能为空")

        import asyncio
        res = asyncio.run(self.mcp_run(rewritten_query))
        # rprint(res)
        datas = json.loads(res.content[0].text).get("pages")

        web_search_docs = [
            {
                "content": item.get("snippet", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": "web"
            }
            for item in datas
        ]

        print(json_format(web_search_docs))

        # return state
        return {"web_search_docs": web_search_docs}

    async def mcp_run(self, rewritten_query):
        token = ConfigMCP.API_KEY
        url = ConfigMCP.MCP_DASHSCOPE_BASE_URL
        async with MCPServerStreamableHttp(
            name="Streamable HTTP Python Server",
            params={
                "url": url,
                "headers":{
                    "Authorization": f"Bearer {token}"
                },
                "timeout": 10
            },
            cache_tools_list=True,
            max_retry_attempts=3,
            client_session_timeout_seconds=30
        ) as server:
            result = await server.call_tool("bailian_web_search", arguments={"query": rewritten_query,"count": 10})
        return result

if __name__ == '__main__':
    node = NodeWebSearchMcp()
    init_state = {
        "item_names": ["RSPRORS-12数字万用表"],
        "rewritten_query": "万用表怎么使用"
    }
    node(init_state)