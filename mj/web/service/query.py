import json
import time
import uuid
from asyncio import Queue

import uvicorn
from fastapi import FastAPI, Path, Body, BackgroundTasks
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from query_process.main_graph import QueryMainGraphRunner
from tool.mongo_tool import get_recent_messages, clear_history
from tool.task_utils import q_dict, get_data, get_q, TASK_STATUS_PROCESSING, update_task_status, TASK_STATUS_COMPLETED, \
    TASK_STATUS_FAILED, put_data, get_task_info

app = FastAPI(
    title="掌柜智库=导入API",
    description="此文档是掌柜智库导入流程的API接口说明"
)

# 添加中间件，解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 开始写接口

# 一、健康请求接口
@app.get("/health")
def get_health():
    return {"status": "ok"}

# 二、获取历史记录接口
@app.get("/history/{session_id}")
def get_history(session_id: str = Path(..., description="用户的会话id")):
    # 获取历史记录：根据session_id从mongoDB里面获取数据
    recent_data = get_recent_messages(session_id)

    # 里面有个_id参数需要处理一下，如果不处理会报错
    recent_data = [
        {
            **data,
            "_id": str(data.get("_id"))
        }
        for data in recent_data
    ]

    # 拿到历史数据之后需要做个排序，按照时间的升序来排：
    recent_data.sort(key=lambda x: x["ts"])

    return {
        "items": recent_data
    }


# 三、清空对话接口
@app.delete("/history/{session_id}")
def delete_history(session_id: str = Path(..., description="根据session_id删除对话记录")):
    clear_history(session_id)
    return {"status": "ok"}

# 四、查询请求
# 该方法用于后台任务的执行，在后台任务中，可以调用langgraph检索流程，并记录当前运行的状态
def start_search_graph(query_str, session_id, task_id):
    # 拿到数据
    q = get_q(task_id)
    init_state = {
        "original_query": query_str,
        "session_id": session_id,
        "task_id": task_id
    }
    try:
        # 设置全局状态
        update_task_status(task_id, TASK_STATUS_PROCESSING)
        # 更新完数据之后，需要拿到最新的数据，然后将最新的数据放到字典的队列里
        put_data(task_id=task_id, event="progress", data=get_task_info(task_id))

        QueryMainGraphRunner.create_and_run(init_state)

        # 更新全局状态
        update_task_status(task_id, TASK_STATUS_COMPLETED)
        # 更新完数据之后，需要拿到最新的数据，然后将最新的数据放到字典的队列里
        put_data(task_id=task_id, event="progress", data=get_task_info(task_id))
    except:
        update_task_status(task_id, TASK_STATUS_FAILED)# 更新完数据之后，需要拿到最新的数据，然后将最新的数据放到字典的队列里
        put_data(task_id=task_id, event="error", data=get_task_info(task_id))
        raise



class QueryParams(BaseModel):
    query: str = Field(..., description="用户的问题")
    session_id: str = Field(..., description="用户会话的id")
@app.post("/query")
def query(
        background_tasks: BackgroundTasks,
        params: QueryParams = Body(..., description="请求体参数")
):
    query_str = params.query
    session_id = params.session_id

    # 创建uuid，使用uuid来当作此次任务的id
    task_id = str(uuid.uuid4())

    # 此处应该在后台任务中调用langgraph去完成检索
    background_tasks.add_task(start_search_graph, query_str, session_id, task_id)


    return {
        "task_id": task_id
    }


# 五、创建SSE订阅的请求接口

# 此方法用来流式输出
def generate_sse(task_id):
    # 首先判断当前的任务id是不是在字典中
    while task_id not in q_dict:
        # 不在字典中则等待直到字典中有该任务的队列了才进行数据的拿取
        time.sleep(1)
    while True:
        # 获取数据并推送
        data = get_data(task_id)
        payload = json.dumps(data.get("data"), ensure_ascii=False)
        yield f"event: {data.get('event')}\ndata: {payload}\n\n"

@app.get("/stream/{task_id}")
def get_stream(task_id: str = Path(..., description="任务ID")):
    return StreamingResponse(generate_sse(task_id), media_type="text/event-stream")




if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001)

