import json

from pymilvus import DataType

from mj.config.config import ConfigMilvus
from mj.config.model_prompt import ITEM_NAME_SYSTEM_PROMPT, ITEM_NAME_USER_PROMPT_TEMPLATE
from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.bgem3_embedding_tool import bgem3_embedding_model, get_bgem3_embedding_model, get_bge3_embedding_vector
from mj.tool.get_milvus_client import get_milvus_client
from mj.tool.get_model_tool import get_model_tool
from mj.tool.json_format_tool import json_format
from mj.tool.logger import logger


class NodeItemNameRecognition(NodeBase):
    """
    主体识别和标签提取
    """
    name = "node_item_name_recognition"

    def process(self, state: ImportGraphState ):
        # 此处处理入口节点的业务逻辑
        # todo 一、获取切分的chunks和文件名校验
        chunks = state.get("chunks")
        file_title = state.get("file_title")

        if not chunks:
            logger.error("切片不能为空！！")
            raise Exception("切片不能为空！！")
        if not file_title:
            logger.error("文件名不能为空！！")
            raise Exception("文件名不能为空！！")

        # todo 二、把chunks的前十个取出来拼成一个串给到大模型并使用模型获取主题名（商品名）
        chunk_str = ""
        for idx,chunk in enumerate(chunks, start=1):
            chunk_str += f"[文件名：{file_title}]\n[章节{idx}:{chunk.get('section_title')}]\n[内容：{chunk.get('section_content')}]\n\n"
            if len(chunk_str) > 10000:
                chunk_str = chunk_str[:10000] if len(chunk_str) > 10000 else chunk_str
                break


        # 获取并调用大模型
        default_model = get_model_tool()
        messages = [
            {"role": "system", "content": ITEM_NAME_SYSTEM_PROMPT},
            {"role": "user", "content": ITEM_NAME_USER_PROMPT_TEMPLATE.format(file_title=file_title, context=chunk_str)}
        ]
        res = default_model.invoke(input=messages)
        # print(res.content)
        # 处理大模型生成的商品主体名
        item_name = res.content.replace("\n", "").replace(" ", "").replace("\t", "")

        # 获取milvus向量数据库的连接
        milvus_client = get_milvus_client()
        collection_name = ConfigMilvus.MILVUS_NAME
        if not milvus_client.has_collection(collection_name):
            # 如果没有数据库，则创建
            # 首先创建1、结构 2、索引 3、表
            schema = milvus_client.create_schema(auto_id=True)
            schema.add_field( # 添加id主键
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True  # 主键
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024  # 必须加维度
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR # 不能加维度
            )

            # 创建索引
            index_params = milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="dense_vector",
                index_type="IVF_FLAT",
                index_name="dense_vector_index",
                metric_type="COSINE", # 求相似度的算法
                params={
                    "nlist": 128, # 把数据分成多少个簇（这里使用的是k-means算法）
                    "nprobe": 10 # 找离query向量最近的几个簇
                }
            )

            index_params.add_index(
                field_name="sparse_vector",
                index_type="SPARSE_INVERTED_INDEX",
                index_name="sparse_vector_index",
                metric_type="IP",
                params={
                    "inverted_index_algo": "DAAT_MAXSCORE"
                }
            )

            milvus_client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )

        # 对数据库表中的数据进行冥等性删除，然后再将数据插入到表中
        embeddings = get_bge3_embedding_vector([item_name])
        dense_vector = embeddings.get("dense")[0]
        sparse_vector = embeddings.get("sparse")[0]

        # 进行冥等性删除
        milvus_client.load_collection(collection_name=collection_name)
        file_title_filter = (
            file_title.replace("\\", "\\\\")
            .replace("\'", "\\'")
            .replace('\"', '\\"')
        )
        filter_condition = f'file_title == "{file_title_filter}"'
        milvus_client.delete(collection_name=collection_name,filter=filter_condition)

        insert_data = {
            "item_name": item_name,
            "file_title": file_title,
            "dense_vector": dense_vector,
            "sparse_vector": sparse_vector
        }

        # 添加数据到数据库中
        milvus_client.insert(collection_name=collection_name, data=insert_data)

        # for chunk in chunks:
        #     chunk = {
        #         **chunk,
        #         "item_name": item_name
        #     }
        chunks = [ {**chunk, "item_name": item_name} for chunk in chunks ]
        # with open(r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\json\item_name_chunks.json", "w", encoding="utf-8") as f:
        #     f.write(json_format(chunks))

        return {
            "chunks": chunks,
            "item_name": item_name
        }


# 此处进行单元测试
if __name__ == "__main__":
    test_node = NodeItemNameRecognition()
    with open(r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\json\document_split_json.json", "r", encoding="utf-8") as f:
        load_chunks = json.load(f)
    init_state = {
        "chunks": load_chunks,
        "file_title": "HAK 180 烫金机",
    }
    test_node(init_state)