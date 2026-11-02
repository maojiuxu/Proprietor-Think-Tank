from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState


class NodeImportMilvus(NodeBase):
    """
    导入milvus持久化数据
    """
    name = "node_import_milvus"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑

        return state


# 此处进行单元测试
if __name__ == "__main__":
    pass