from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState


class NodeEntry(NodeBase):
    """
    该类作为入口节点主要用来校验用户传来的文件地址
    """
    name = "node_entry"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑

        return state


# 此处进行单元测试
if __name__ == "__main__":
    pass