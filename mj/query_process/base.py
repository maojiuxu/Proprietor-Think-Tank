# atguigu/query_process/base.py

"""
查询流程节点基类

定义统一的节点接口规范，提供通用功能
"""
from abc import abstractmethod, ABC

from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from tool.task_utils import get_q, add_running_task, put_data, add_done_task, get_task_info


class NodeBase(ABC):

    name: str = "node_base"

    def __init__(self):
        """
        强制子类设置name
        """
        if self.name == "node_base":
            raise ValueError(f"{self.__class__.__name__} 必须设置 name 属性")

    def __call__(self, state: QueryGraphState):
        """
        节点执行入口
        """
        try:
            task_id = state.get("task_id")
            q = get_q(task_id=task_id)
            add_running_task(task_id, self.name)
            put_data(task_id, event="progress", data=get_task_info(task_id))
            logger.info(f"{self.name} 开始执行...")

            result = self.process(state)

            logger.info(f"{self.name} 结束执行...")
            add_done_task(task_id, self.name)
            put_data(task_id, event="progress", data=get_task_info(task_id))

            return result
        except Exception as e:
            logger.error(f"{self.name} 执行失败: {e}")
            raise

    @abstractmethod
    def process(self, state: QueryGraphState):
        """
        节点的核心处理逻辑
        :return:
        """
        pass