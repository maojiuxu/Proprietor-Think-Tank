import json
import shutil
import time
import zipfile
from pathlib import Path
from zipfile import ZipFile

import requests

from mj.config.config import ConfigMineru
from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.logger import logger


class NodePDFToMD(NodeBase):
    """
    该类使用mineru将pdf文档转为md文档
    """
    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState ):
        """
        此处处理文档转换业务逻辑
        :param state:
        :return:
        """
        pdf_path = state.get("pdf_path") # 上传的pdf文件路径，用来给mineru
        local_dir = state.get("local_dir") # mineru服务器转换文档后返回的文件下载到本地的路径

        # 1、检查本地路径是否有问题
        if not pdf_path:
            logger.error("上传文件路径不存在！")
            raise Exception("上传文件路径不存在！")
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            logger.error("上传文件不存在！（文件路径不正确！）")
            raise Exception("上传文件不存在！（文件路径不正确！）")

        if not local_dir:
            logger.error("输出文件路径不存在！")
            raise Exception("输出文件路径不存在！")
        local_dir_obj = Path(local_dir)
        if not local_dir_obj.exists():
            # 没有文件夹则创建文件夹：parents=True代表递归创建文件夹；exist_ok=True代表有文件夹时也不报错
            local_dir_obj.mkdir(parents=True, exist_ok=True)

        # 2、发送请求，将文档上传到mineru
        token = ConfigMineru.mineru_token
        url = "https://mineru.net/api/v4/file-urls/batch"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "files": [
                {"name": pdf_path_obj.name, "data_id": "abcd"}
            ],
            "model_version": "vlm"
        }
        file_path = [pdf_path]
        response = requests.post(url, headers=header, json=data)
        if response.status_code != 200:
            logger.error("mineru请求失败！")
            raise Exception("mineru请求失败！")

        result = response.json()
        if result["code"] != 0:
            logger.error("请求成功，但是返回的数据不对！")
            raise Exception("请求成功，但是返回的数据不对！")
        # 获取到batch_id
        batch_id = result["data"]["batch_id"]
        print("==============")
        print("batch_id：", batch_id)

        urls = result["data"]["file_urls"]
        for i in range(0, len(urls)):
            with open(file_path[i], 'rb') as f:
                res_upload = requests.put(urls[i], data=f)
                if res_upload.status_code == 200:
                    logger.info(f"{urls[i]} 上传成功")
                else:
                    logger.info(f"{urls[i]} 上传失败")

        # 3、根据batch_id轮询查询mineru的信息
        total_time = 300 # 轮询获取结果的超时时间
        start_time = time.time()
        while True:
            try:
                # 在此处发送请求
                token = ConfigMineru.mineru_token
                # batch_id = batch_id
                url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
                header = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                }

                res = requests.get(url, headers=header)
                if res.status_code != 200:
                    logger.error("文件上传解析请求失败！")
                    raise Exception("文件上传解析请求失败！")

                if not res.json()["data"]:
                    logger.error("请求成功，但是返回数据失败！")
                    raise Exception("请求成功，但是返回数据失败！")

                req_state = res.json().get("data").get("extract_result")[0].get("state")
                if req_state == "waiting-file":
                    logger.warning("数据上传等待中，请稍后再试")
                    raise Exception("数据上传等待中，请稍后再试")
                elif req_state == "running":
                    logger.warning("文档解析中，请稍等...")
                    raise Exception("文档解析中，请稍等...")
                elif req_state == "done":
                    logger.info("文档解析完成！！！")
                    url = res.json().get("data").get("extract_result")[0].get("full_zip_url")
                    print("解析后的文档下载地址为：", url)
                    break

                # print("==============")
                # print(res.status_code)
                # print(json.dumps(res.json()))
                # print(json.dumps(res.json()["data"]))
                # print(json.dumps(res.json()["data"].get("extract_result")[0].get("state")))
                # print("==============")
            except Exception as e:
                if time.time() - start_time > total_time:
                    logger.error("使用mineru解析文档超时，请稍后再试！！！")
                    break

        # 4、拿到mineru的返回地址之后，将文档下载到本地
        result = requests.get(url)
        if result.status_code != 200:
            logger.error("获取压缩包请求失败！")
            raise Exception("获取压缩包请求失败！")

        zip_content = result.content
        zip_path_obj = local_dir_obj / f"{pdf_path_obj.stem}.zip"
        with open(zip_path_obj, "wb") as f:
            f.write(zip_content)

        # 5、解压下载后的文件到指定路径
        unzip_path_obj = local_dir_obj / pdf_path_obj.stem

        # 判断解压目录是否存在，存在则删除后再重新创建（保证幂等性）
        if unzip_path_obj.exists():
            shutil.rmtree(unzip_path_obj)
        unzip_path_obj.mkdir(parents=True, exist_ok=True)

        # 读取压缩文件的内容，并将其解压到文件夹中
        with zipfile.ZipFile(zip_path_obj) as zip_ref:  # 打开压缩包拿到操作对象
            zip_ref.extractall(unzip_path_obj)   # 将压缩包中的数据解压到指定文件夹中

        # 6、修改文件名
        full_md_obj = unzip_path_obj / "full.md"
        final_md_obj = full_md_obj.with_name(f"{pdf_path_obj.stem}.md")   # 在内存中改名，但是暂未落盘
        full_md_obj.rename(final_md_obj)   # 改名最终落盘

        # 读取md文档的内容，并将其更新到state
        with open(final_md_obj, "rb") as f:
            md_content = f.read()

        # 7、返回数据增量
        return {
            "md_path": str(final_md_obj),
            "md_content": md_content
        }


# 此处进行单元测试
if __name__ == "__main__":
    state = {
        "pdf_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\hak180产品安全手册.pdf",
        "local_dir": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output"
    }
    NodePDFToMD()(state)