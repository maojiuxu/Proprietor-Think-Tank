import os
import dashscope

from mj.config.config import ConfigRerank

# 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的region取值不同。
client = dashscope.Client(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    # 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    api_key=ConfigRerank.RERANK_API_KEY,
    workspace=ConfigRerank.WORKSPACE_ID,
    region="cn-beijing",
)

def text_rerank(query,documents):
    resp = client.rerank.create(
        model="qwen3.7-text-rerank",
        query=query,
        documents=documents,
        top_n=len(documents),
        return_documents=False,
        instruct="Given a web search query, retrieve relevant passages that answer the query."
    )
    return [
        {
            "index":item.index,
            "score":item.relevance_score
        }
        for item in resp.results
    ]

if __name__ == '__main__':
    result = text_rerank(query="我爱谁", documents=["我爱杨幂","我爱赵丽颖"])
    print(result)