import base64
import json
import mimetypes
import os
import re
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from anyio import sleep
from langchain.chat_models import init_chat_model
from minio.deleteobjects import DeleteObject
from openai import base_url

from mj.config.config import ConfigVLM, ConfigMinio
from mj.config.const import ConstValue
from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.logger import logger
from mj.tool.minio_client_tool import get_minio_client


class NodeMDImg(NodeBase):
    """
    该类处理md文档中的图片
    """
    name = "node_md_img"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑
        # 一、首先将图片以及图片的上下文传给大模型，让大模型提取摘要并保存
        # 1、获取到images文件夹中的所有子项
        image_dir_obj, list_images, md_content, md_path_obj = self.get_list_image(state)

        # 2、遍历images子项的列表，然后使用正则匹配到图片在md文件中的位置并获取图片的上下文信息
        list_images_info = self.get_list_images_info(image_dir_obj, list_images, md_content)

        # 3、将图片传给视觉模型得到图片的摘要
        list_summary_image = self.get_image_summary(list_images_info)

        # 接下来需要将图片上传到minio服务端并获取url，然后将url和上面得到的summary替换到md文档中
        # 4、首先将图片上传到minio服务端并获取url，为了保证，上传之前需要将数据库中的文件递归删除
        image_with_summary_url_list = self.get_minio_summary_url_list(list_summary_image, md_path_obj)

        # 5、然后将url和上面得到的summary替换到md文档中
        md_content = self.get_new_md_content(image_with_summary_url_list, md_content, md_path_obj)

        # 最后更新state
        return {
            "md_path":str(md_path_obj.parent / f"{md_path_obj.stem}_new.md"),
            "md_content":md_content
        }

    def replace_image_reference(
            self,
            md_content: str,
            image_name: str,
            image_url: str,
            image_summary: str,
    ):

        escaped_name = re.escape(image_name)

        # HTML 图片引用
        html_pattern = (
            rf'<img\b'
            rf'(?=[^>]*\bsrc\s*=\s*["\'][^"\']*{escaped_name}["\'])'
            rf'[^>]*>'
        )

        def replace_html(match):
            tag = match.group()

            # 替换 src 属性
            tag = re.sub(
                r'(\bsrc\s*=\s*["\'])[^"\']*(["\'])',
                lambda m: m.group(1) + image_url + m.group(2),
                tag,
                count=1,
            )

            return f"{tag}\n\n> 图片总结：{image_summary}"

        md_content = re.sub(
            html_pattern,
            replace_html,
            md_content,
        )

        # Markdown 图片引用
        markdown_pattern = (
            rf'!\[([^\]]*)\]'
            rf'\([^)]*{escaped_name}[^)]*\)'
        )

        def replace_markdown(match):
            description = match.group(1)

            image_reference = f"![{description}]({image_url})"

            return (
                f"{image_reference}\n\n"
                f"> 图片总结：{image_summary}"
            )

        md_content = re.sub(
            markdown_pattern,
            replace_markdown,
            md_content,
        )

        return md_content

    def get_new_md_content(self, image_with_summary_url_list: list[Any], md_content: str, md_path_obj: Path) -> str:
        for image_with_summary_url in image_with_summary_url_list:
            # # 利用正则直接替换
            # pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_with_summary_url.get('image_name')) + r"\)")
            # # 替换后，更新文档内容
            # md_content = pattern.sub(
            #     lambda _: f"![{image_with_summary_url.get("summary")}]({image_with_summary_url.get("url")})",
            #     md_content)
            md_content = self.replace_image_reference(
                md_content=md_content,
                image_name=image_with_summary_url.get('image_name'),
                image_url=image_with_summary_url.get("url"),
                image_summary=image_with_summary_url.get("summary")
            )

        # 将更新后的文档重新写入文件并将其保存在原文档的同级目录
        with open(md_path_obj.parent / f"{md_path_obj.stem}_new.md", "w", encoding="utf-8") as f:
            f.write(md_content)
        return md_content

    def get_minio_summary_url_list(self, list_summary_image: list[Any], md_path_obj: Path) -> list[Any]:
        # 4.1、删除minio服务器上的文件
        # 该变量用来再minio服务上存储文件的地址
        upload_path = f"{ConfigMinio.MINIO_BUCKET_DIR}/{datetime.now().strftime('%Y%m%d')}/{md_path_obj.stem}"

        # 获取minio连接实例
        minio_client = get_minio_client()

        # 先将已经存在的文件或者目录列出来
        exist_file_generator = minio_client.list_objects(  # exist_file_list是一个生成器
            bucket_name=ConfigMinio.MINIO_BUCKET_NAME,
            prefix=upload_path
        )
        exist_file_list = [DeleteObject(exist.object_name) for exist in exist_file_generator]

        # Remove list of objects.
        minio_client.remove_objects(bucket_name=ConfigMinio.MINIO_BUCKET_NAME, delete_object_list=exist_file_list)

        # 4.2、现在遍历 list_summary_image 然后上传文件到minio服务器并获取到图片的url
        image_with_summary_url_list = []
        for summary_image in list_summary_image:
            # Upload data.
            minio_client.fput_object(
                bucket_name=ConfigMinio.MINIO_BUCKET_NAME,
                object_name=upload_path + "/" + summary_image.get("image_name"),
                file_path=summary_image.get("image_path"),
            )

            # 可以使用这个SDK直接获取到url，但是这个方式获取到的url里面含有很多没用的信息，所以选择下面的方式自己去拼接url
            # url = minio_client.get_presigned_url(
            #     method="GET",
            #     bucket_name=MinioConfig.minio_bucket_name,
            #     object_name=upload_dir + image_with_summary.get("image_name"),
            # )
            # print(url)

            url = f"http://{ConfigMinio.MINIO_ENDPOINT}/{ConfigMinio.MINIO_BUCKET_NAME}/{upload_path}/{summary_image.get("image_name")}"
            # print(f"{summary_image.get("image_name")}的路径：{url}")

            # 现在已经获取到url，所以把url包装一下返回
            image_with_summary_url_list.append({
                **summary_image,
                "url": url
            })
        return image_with_summary_url_list

    def get_image_summary(self, list_images_info: list[Any]) -> list[Any]:
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
                wait_time = 60 - (time.time() - dp_time[0])
                sleep(wait_time)
                # 此时需要抛出超过一分钟但是仍然还在队列中的时间
                while len(dp_time) > 0 and time.time() - dp_time[0] > 60:
                    dp_time.popleft()

            # 此时的队列必然有位置，所以直接将数据加入进去
            dp_time.append(time.time())

            # 在此处调用大模型，但是在调用之前需要将图片转为url才能放到messages里面去使用
            mime_type, _ = mimetypes.guess_type(image_info.get("image_path"))
            with open(str(image_info.get("image_path")), "rb") as f:
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
                "image_path": str(image_info.get("image_path")),
            })
        print("***********************************************************")
        print(json.dumps(list_summary_image, ensure_ascii=False, indent=4))
        print("***********************************************************")
        return list_summary_image

    def get_list_images_info(self, image_dir_obj: list[str], list_images: Path, md_content: str) -> list[Any]:
        list_images_info = []
        IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        for image_name in list_images:
            # 2.1、首先判断该文件是否是图片类型
            image_path_obj = image_dir_obj / image_name
            suffix = image_path_obj.suffix
            if suffix not in IMAGE_EXTENSIONS:  # 如果不是图片则直接跳过
                continue
            # 2.2、是图片，则直接根据图片的名称在md内容中进行匹配
            # pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_name) + r"\)")
            pattern = re.compile(
                rf'<img\b(?=[^>]*\bsrc\s*=\s*["\'][^"\']*{image_name}[^"\']*["\'])[^>]*>'
                rf'|'
                rf'!\[[^\]]*\]\([^)]*{image_name}[^)]*\)'
            )
            match = pattern.search(md_content)
            if not match:
                logger.warning(f"文档中未使用该图片：{image_name}")
                continue
            start, end = match.span()  # 获取到匹配到的起始和结束位置
            pre_text = md_content[max(start - 200, 0):start]
            post_text = md_content[end:min(len(md_content), end + 200)]
            list_images_info.append({
                "image_name": image_name,
                "image_path": image_path_obj,
                "pre_text": pre_text,
                "post_text": post_text,
            })
        return list_images_info

    def get_list_image(self, state: ImportGraphState) -> tuple[list[str], Path, str, Path]:
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
        return image_dir_obj, list_images, md_content, md_path_obj


# 此处进行单元测试
if __name__ == "__main__":
    node_md_img = NodeMDImg()
    state = {
        # "md_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\hak180产品安全手册\hak180产品安全手册.md"
        "md_path": r"E:\SZ_AIAgent\260817\16-掌柜智库\day01\课件\01【掌柜智库】项目简介.md"
    }
    node_md_img(state)