import base64
import json
import mimetypes
import os
import re
import time
from collections import deque
from pathlib import Path

from anyio import sleep
from langchain.chat_models import init_chat_model
from openai import base_url

from mj.config.config import ConfigVLM
from mj.config.const import ConstValue
from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.logger import logger

class NodeMDImg(NodeBase):
    """
    该类处理md文档中的图片
    """
    name = "node_md_img"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑
        # 一、首先将图片以及图片的上下文传给大模型，让大模型提取摘要并保存
        # 1、获取到images文件夹中的所有子项
        md_path = state.get("md_path")
        if not md_path:
            logger.error("路径不能为空")
            raise Exception("路径不能为空")
        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("文件不存在")
            raise Exception("文件不存在")

        image_dir_obj = md_path_obj.parent / "images"  # 图片目录对象
        if not image_dir_obj.exists():
            logger.error("图片的文件夹不存在")
            raise Exception("图片的文件夹不存在")

        with open(md_path_obj, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 获取到图片文件列表
        list_images = os.listdir(image_dir_obj)  # 获取到images目录下的所有文件和文件夹名称汇总成一个list返回
        # print(json.dumps(list_images, ensure_ascii=False, indent=4))

        if len(list_images) == 0:
            logger.error("images文件夹中不存在文件和文件夹")
            raise Exception("images文件夹中不存在文件和文件夹")

        # 2、遍历images子项的列表，然后使用正则匹配到图片在md文件中的位置并获取图片的上下文信息
        list_images_info = []
        IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        for image_name in list_images:
            # 2.1、首先判断该文件是否是图片类型
            image_name_obj = image_dir_obj / image_name
            suffix = image_name_obj.suffix
            if suffix not in IMAGE_EXTENSIONS: # 如果不是图片则直接跳过
                continue
            # 2.2、是图片，则直接根据图片的名称在md内容中进行匹配
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_name) + r"\)")
            match = pattern.search(md_content)
            if not match:
                logger.warning(f"文档中未使用该图片：{image_name}")
                continue
            start, end = match.span() # 获取到匹配到的起始和结束位置
            pre_text = md_content[max(start-200, 0):start]
            post_text = md_content[end:min(len(md_content), end+200)]
            list_images_info.append({
                "image_name": image_name,
                "image_name_obj": image_name_obj,
                "pre_text": pre_text,
                "post_text": post_text,
            })

        # 3、将图片传给视觉模型得到图片的摘要
        list_summary_image = []
        # 实例化一个模型
        vlm = init_chat_model(
            model=ConfigVLM.V_MODEL_NAME,
            model_provider="openai",
            base_url=ConfigVLM.V_MODEL_BASE_URL,
            api_key=ConfigVLM.V_MODEL_API_KEY,
            temperature=ConfigVLM.V_MODEL_TEMPERATURE
        )
        # 定义一个双端队列用来存储每次调用大模型的时间戳
        # 因为大模型的调用是有频率限制的（比如一分钟内的调用不得超过3000次）
        # 所以定义一个队列用来控制模型调用的频率

        dp_time = deque(maxlen=ConstValue.dp_maxlen)
        for image_info in list_images_info:
            # 首先检查队列中是否有超时的，如果有，则直接踢出去
            while len(dp_time) > 0 and time.time() - dp_time[0] > 60:
                dp_time.popleft()

            # 此时再看队列是否有空位置
            if len(dp_time) >= ConstValue.dp_maxlen:
                # 此时等待
                wait_time = 60- (time.time() - dp_time[0])
                sleep(wait_time)
                # 此时需要抛出超过一分钟但是仍然还在队列中的时间
                while len(dp_time) > 0 and time.time() - dp_time[0] > 60:
                    dp_time.popleft()

            # 此时的队列必然有位置，所以直接将数据加入进去
            dp_time.append(time.time())

            # 在此处调用大模型，但是在调用之前需要将图片转为url才能放到messages里面去使用
            mime_type, _ = mimetypes.guess_type(image_info.get("image_name_obj"))
            with open(str(image_info.get("image_name_obj")), "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                        {"type": "text", "text": f"""这是一张图片，图片上文部分为"{image_info.get("pre_text")}"，
                                     下文部分为"{image_info.get("post_text")}"，
                                     请用中文简要总结这张图片的摘要,字数在50字以内。"""},
                    ],
                },
            ]

            res = vlm.invoke(input=messages)
            # print("===========================")
            # print(res.content)
            list_summary_image.append({
                "summary": res.content,
                "image_name": image_info.get("image_name"),
                "image_path": str(image_info.get("image_path_obj")),
            })

        print(json.dumps(list_summary_image, ensure_ascii=False, indent=4))






        return state


# 此处进行单元测试
if __name__ == "__main__":
    node_md_img = NodeMDImg()
    state = {
        "md_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\hak180产品安全手册\hak180产品安全手册.md"
    }
    node_md_img(state)