# 该界面使用fastapi接收前端发送的请求
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path

import fastapi
import uvicorn
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware


from config.config import ConfigMinio
from import_process.main_graph import MainGraph
from tool.minio_client_tool import get_minio_client
from tool.task_utils import get_task_info, update_task_status, TASK_STATUS_PROCESSING, TASK_STATUS_COMPLETED, \
    TASK_STATUS_FAILED, add_running_task, add_done_task, add_node_duration

# 1、首先定义一个app
app = FastAPI(
    title="掌柜智库-导入API",
    description="此文档是掌柜智库导入流程的API接口说明"
)

# 2、在FastAPI实例上添加中间件来解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)

def start_import_graph(task_id: str, output_file_dir: str, local_file_path: str):
    init_state = {
        "task_id": task_id,
        "local_dir": output_file_dir,
        "local_file_path": local_file_path,
    }
    try:
        MainGraph.create_and_run(init_state)
        # 如果这个模块能够顺利走完，则状态为结束
        update_task_status(task_id, TASK_STATUS_COMPLETED)
    except:
        # 如果上面报错，则状态更新为：失败
        update_task_status(task_id, TASK_STATUS_FAILED)
        raise

# 此处定义一个post请求，来处理前端发来的请求
@app.post("/upload")
def upload( background_task: BackgroundTasks, file: UploadFile = File(..., description="需要上传的文件")):
    # 首先生成本次任务的id
    task_id = str(uuid.uuid4())

    # 开始本次任务，此时整体的任务状态为处理中
    update_task_status(task_id, TASK_STATUS_PROCESSING)
    start_time = time.time()
    add_running_task(task_id, "upload_file")

    # 1、接收到前端传来的文件后，需要把文件首先存储在本地磁盘中
    output_file_dir = rf"D:\output\{datetime.now().strftime('%Y%m%d')}" # 输出的文件夹
    local_file_path = f"{output_file_dir}/{file.filename}"  # 输出的文件路径(即存储在本地磁盘中的文件路径)
    output_file_dir_obj = Path(output_file_dir)  # 输出的文件夹路径对象

    # 此处判断文件夹是否存在
    if not output_file_dir_obj.exists():
        # 不存在则直接创建文件夹
        output_file_dir_obj.mkdir(parents=True, exist_ok=True)
    # 然后打开文件，并将文件写入
    with open(local_file_path, "wb") as f:
        shutil.copyfileobj(file.file, f, length=1024*1024*10)# 直接将文件拷贝到磁盘中

    # 2、然后将文件上传到minio转储
    minio_client = get_minio_client()
    minio_client.fput_object(
        bucket_name=ConfigMinio.MINIO_BUCKET_NAME,
        object_name=f"upload_file/{datetime.now().strftime('%Y%m%d')}/{file.filename}",
        file_path=local_file_path
    )

    add_done_task(task_id, "upload_file")
    add_node_duration(task_id, "upload_file", time.time() - start_time)

    # 3、然后调用第一个模块的maingraph去处理文件并入库
    background_task.add_task(start_import_graph, task_id, output_file_dir, local_file_path)

    return {
        "task_id": task_id
    }


# 定义前端获取当前文件上传任务的状态获取接口，用于前端的状态轮询
@app.get("/status/{task_id}")
def get_status(task_id: str = fastapi.Path(..., description="本次任务的id")):
    return get_task_info(task_id)

# 启动项目来测试是否能用
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)




