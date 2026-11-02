from pathlib import Path

from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.logger import logger


class NodeEntry(NodeBase):
    """
    该类作为入口节点主要用来校验用户传来的文件地址
    """
    name = "node_entry"

    def process(self, state: ImportGraphState ):
        """
        此处处理入口节点的业务逻辑
        :param state:
        :return:
        """
        # 1、首先获取到用户上传的原始文件路径
        local_file_path = state.get("local_file_path")

        # 2、判断提取出来的路径有没有问题
        if not local_file_path:
            logger.error("上传的文件路径不能为空")
            raise ValueError("上传的文件路径不能为空")

        # 获取到文件对象
        local_file_path_obj = Path(local_file_path)
        if not local_file_path_obj.exists():
            logger.error("文件不存在！文件路径无效")
            raise ValueError("文件不存在！文件路径无效")

        # 文件存在，则直接获取文件的类型、名称、以及所在的文件夹
        print("======================")
        print("文件名（不带后缀）：", local_file_path_obj.stem)
        print("文件名（带后缀）：", local_file_path_obj.name)
        print("文件后缀：", local_file_path_obj.suffix)
        print("======================")

        # 根据文件的后缀来更新数据
        if local_file_path_obj.suffix == ".pdf":
            logger.info("文件上传成功，识别为 pdf 类型文件~")
            return {
                "file_title": local_file_path_obj.stem,
                "pdf_path": local_file_path,
                "is_pdf_read_enabled": True
            }
        elif local_file_path_obj.suffix == ".md":
            logger.info("文件上传成功，识别为 md 类型文件~")
            return {
                "file_title": local_file_path_obj.stem,
                "md_path": local_file_path,
                "is_md_read_enabled": True
            }
        else:
            logger.error("暂不支持除pdf、md格式以外的文件格式！！！")
            raise Exception("暂不支持除pdf、md格式以外的文件格式！！！")


# 此处进行单元测试
if __name__ == "__main__":
    node_entry = NodeEntry()
    state = {
        "local_file_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\hak180产品安全手册.pdf", # pdf文档
        # "local_file_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\markdown测试文件.md", # md文档
        # "local_file_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\word文档测试文件.docx", # 其他文档
    }
    node_entry(state)