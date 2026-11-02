import time
from abc import ABC, abstractmethod

from mj.import_process.state import ImportGraphState
from mj.tool.logger import logger


# 所有节点的基类
class NodeBase(ABC):
    name = "base_node"

    def __init__(self):
        # 子类初始化实例时，在此处校验子类是否有name属性
        if self.name == "base_node":
            # 此时说明子类没有设置name属性，应该报错
            logger.error(f"子类--{self.__class__.name}--未添加name属性")
            # 然后直接抛出异常
            raise ValueError(f"子类--{self.__class__.name}--未添加name属性")

    # 所有的子类中都不会重写__call__方法，所以子类的实例被Graph当作函数调用时，都会调用这里的__call__方法
    def __call__(self, state):
        # 在此处我们可以对所有子类的异常进行处理，同时可以打印日志信息
        try:
            logger.info(f"{self.name}开始调用__call__方法处理业务...")
            self.process(state)
            logger.info(f"{self.name}节点的业务处理完毕！！！")
        except Exception as e:
            logger.error(f"{self.name} 节点报错？？？出问题了--")
            raise ValueError(f"{self.name} 节点报错？？？出问题了--")

    @abstractmethod
    def process(self, state: ImportGraphState):
        pass

#region 此处作为该节点的单元测试
# if __name__ == '__main__':
#     # 首先定义子类节点
#     class TestNode(NodeBase):
#         name = "test_node"
#         def process(self, state):
#             logger.info(f"调用 {self.name} 节点的process方法！")
#
#     # 实例化类
#     test_node = TestNode()
#
#     # 随便创建状态
#     state = {
#         "abc": "123"
#     }
#
#     # 模拟graph底层将实例化对象当作函数来执行
#     res = test_node(state)
#endregion