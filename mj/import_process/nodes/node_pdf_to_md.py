from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState


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
        local_path = state.get("local_path") # mineru服务器转换文档后返回的文件下载到本地的路径

        return state


# 此处进行单元测试
if __name__ == "__main__":
    pass