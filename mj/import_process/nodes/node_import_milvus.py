import json

from pymilvus import DataType

from mj.config.config import ConfigMilvus
from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.get_milvus_client import get_milvus_client
from mj.tool.logger import logger
from rich import print as rprint


class NodeImportMilvus(NodeBase):
    """
    导入milvus持久化数据
    """
    name = "node_import_milvus"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑
        # 将上一个节点得到的带有稠密和稀疏向量的chunks存储到数据库中
        file_title = state.get("file_title")
        chunks = state.get("chunks")
        if not file_title:
            logger.error("file_title不能为空！！！")
            raise Exception("file_title不能为空")
        if not chunks:
            logger.error("chunks不能为空！！！")
            raise Exception("chunks不能为空")

        # 获取client连接实例，并做冥等性删除
        milvus_client = get_milvus_client()
        collection_name = ConfigMilvus.MILVUS_CHUNKS_COLLECTION_NAME

        if not milvus_client.has_collection(collection_name=collection_name):
            # 如果表不存在，则直接创建，创建表分为三部：创建表结构、创建索引、创建表
            # 1、创建表结构
            schema = milvus_client.create_schema(auto_id=True)
            schema.add_field(
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True
            ).add_field(
                field_name="section_title",
                datatype=DataType.VARCHAR,
                max_length=500
            ).add_field(
                field_name="file_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="section_content",
                datatype=DataType.VARCHAR,
                max_length=5000
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="part",
                datatype=DataType.INT64
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR
            )

            # 创建索引
            index_params = milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="dense_vector",
                index_type="IVF_FLAT",
                index_name="dense_vector_index",
                metric_type="COSINE",
                params={
                    "nlist": 128,
                    "nprobe": 10
                }
            )
            index_params.add_index(
                field_name="sparse_vector",
                index_type="SPARSE_INVERTED_INDEX",
                index_name="sparse_vector_index",
                metric_type="IP",
                params={"inverted_index_algo": "DAAT_MAXSCORE"}
            )

            milvus_client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )

        # 做冥等性删除
        # 1、加载数据collection
        milvus_client.load_collection(collection_name=collection_name)
        # 2、对文件名做处理，然后再做冥等性删除
        file_title_filter = (file_title
                             .replace("\\", "\\\\")
                             .replace("\'", "\\'")
                             .replace('\"', '\\"'))
        file_title_condition = f"file_name == '{file_title_filter}'"
        milvus_client.delete(collection_name=collection_name, filter=file_title_condition)

        # milvus_client.load_collection(collection_name=collection_name)
        # file_title_filter = (
        #     file_title.replace("\\", "\\\\")
        #     .replace("\'", "\\'")
        #     .replace('\"', '\\"')
        # )
        # filter_condition = f'file_title == "{file_title_filter}"'
        # milvus_client.delete(collection_name=collection_name, filter=filter_condition)

        # 添加数据
        res = milvus_client.insert(collection_name=collection_name, data=chunks)
        # print("最终结果：=========================================")
        # rprint(res)
        # 回填入库时自动给的id值到每个chunk,其实没什么用，目的就是为了state最终存储数据保证完整
        for idx, chunk in enumerate(chunks):
            # chunk["id"] = res.get("ids").pop(0)
            chunk["id"] = res.get("ids")[idx]
        return {
            "chunks": chunks
        }


# 此处进行单元测试
if __name__ == "__main__":
    node = NodeImportMilvus()
    with open(r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\json\bgem3_embedding_chunks.json", 'r', encoding="utf-8") as f:
        load_chunks = json.load(f)
    init_state = {
        "chunks": load_chunks,
        "file_title": "hak180产品安全手册_new"
    }
    node(init_state)