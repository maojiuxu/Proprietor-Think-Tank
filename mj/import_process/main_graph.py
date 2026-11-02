from langgraph.constants import END
from langgraph.graph import StateGraph

from mj.import_process.nodes.node_bge_embedding import NodeBGEEmbedding
from mj.import_process.nodes.node_document_split import NodeDocumentSplit
from mj.import_process.nodes.node_entry import NodeEntry
from mj.import_process.nodes.node_import_milvus import NodeImportMilvus
from mj.import_process.nodes.node_item_name_recognition import NodeItemNameRecognition
from mj.import_process.nodes.node_md_img import NodeMDImg
from mj.import_process.nodes.node_pdf_to_md import NodePDFToMD
from mj.import_process.state import ImportGraphState


class MainGraph:
    def __init__(self):
        # 1、创建构建器
        self.builder = StateGraph(state_schema=ImportGraphState)

        # 2、添加类节点
        self.add_nodes()

        # 3、添加边
        self.add_edges()

        # 4、创建空图 graph
        self.graph = None


    # builder添加类节点
    def add_nodes(self):
        self.builder.add_node(NodeEntry.name, NodeEntry())
        self.builder.add_node(NodePDFToMD.name, NodePDFToMD())
        self.builder.add_node(NodeMDImg.name, NodeMDImg())
        self.builder.add_node(NodeDocumentSplit.name, NodeDocumentSplit())
        self.builder.add_node(NodeItemNameRecognition.name, NodeItemNameRecognition())
        self.builder.add_node(NodeBGEEmbedding.name, NodeBGEEmbedding())
        self.builder.add_node(NodeImportMilvus.name, NodeImportMilvus())

    # builder添加边
    def add_edges(self):
        # self.builder.set_entry_point("node_entry")
        self.builder.add_edge("__start__", NodeEntry.name)
        self.builder.add_conditional_edges(NodeEntry.name, self.document_type_identification, {
            "node_pdf_to_md": NodePDFToMD.name,
            "node_md_img": NodeMDImg.name,
            "END": END
        })
        self.builder.add_edge(NodePDFToMD.name, NodeMDImg.name)
        self.builder.add_edge(NodeMDImg.name, NodeDocumentSplit.name)
        self.builder.add_edge(NodeDocumentSplit.name, NodeItemNameRecognition.name)
        self.builder.add_edge(NodeItemNameRecognition.name, NodeBGEEmbedding.name)
        self.builder.add_edge(NodeBGEEmbedding.name, NodeImportMilvus.name)
        self.builder.add_edge(NodeImportMilvus.name, END)

    # 条件边的方法
    def document_type_identification(self, state):
        is_pdf_read_enabled = state.get("is_pdf_read_enabled")
        is_md_read_enabled = state.get("is_md_read_enabled")
        if is_pdf_read_enabled:
            return "node_pdf_to_md"
        elif is_md_read_enabled:
            return "node_md_img"
        else:
            return "END"


    # 实例调用这个图
    def run(self, state):
        if not self.graph:
            self.graph = self.builder.compile()
        res = self.graph.invoke(state)
        return res

    # 创建一个类方法用来直接构建并运行graph
    @classmethod
    def create_and_run(cls, state):
        return cls().run(state)


# if __name__ == "__main__":
#     state = {
#         "local_file_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\hak180产品安全手册.pdf",  # pdf文档
#         # "local_file_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\markdown测试文件.md", # md文档
#         # "local_file_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\word文档测试文件.docx", # 其他文档
#     }
#     MainGraph.create_and_run(state)