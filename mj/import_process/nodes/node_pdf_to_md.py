from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState


class NodePDFToMD(NodeBase):
    """
    该类使用mineru将pdf文档转为md文档
    """
    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑

        return state


# 此处进行单元测试
if __name__ == "__main__":
    pass