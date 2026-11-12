from pymilvus import MilvusClient, AnnSearchRequest, WeightedRanker

from mj.config.config import ConfigMilvus

milvus_client = None

def get_milvus_client():
    global milvus_client
    if milvus_client is None:
        milvus_client = MilvusClient(
            uri=ConfigMilvus.MILVUS_URL
        )
    return milvus_client

def get_ann_search_req(
        dense_vector,
        sparse_vector,
        limit=10,
        dense_param=None,
        sparse_param=None,
        expr=None
):
    """
    根据稠密和稀疏向量获取到指定的AnnSearchRequest数据
    :param dense_vector: 需要检索的稠密向量
    :param sparse_vector: 需要检索的稀疏向量
    :param limit: 需要从数据库中召回的条数
    :param dense_param: 稠密向量做相似度检索的算法
    :param sparse_param: 稀疏向量做相似度检索的方法
    :param expr: 检索的过滤条件
    :return: 将检索到的数据返回回去
    """
    if dense_param is None:
        # 稠密向量默认使用正余弦的算法来计算相似度
        dense_param ={
            "metric_type": "COSINE"
        }
    if sparse_param is None:
        # 稀疏向量默认使用内积的方式来计算向量的相似度
        sparse_param = {
            "metric_type": "IP"
        }
    dense_req = AnnSearchRequest(
        data=[dense_vector],
        anns_field="dense_vector",
        limit=limit,
        param=dense_param,
        expr=expr
    )
    sparse_req = AnnSearchRequest(
        data=[sparse_vector],
        anns_field="sparse_vector",
        limit=limit,
        param=sparse_param,
        expr=expr
    )
    return [dense_req, sparse_req]

# 做权重混合检索
def get_hybrid_search_res(
    collection_name,
    reqs,
    limit=10,
    output_fields=[],
    ranker=(0.5, 0.5),
):
    milvus_client = get_milvus_client()
    weighted_ranker = WeightedRanker(*ranker) #加权排名排序器
    res = milvus_client.hybrid_search(
        collection_name=collection_name,
        reqs=reqs,
        ranker=weighted_ranker,
        limit=limit,
        output_fields=output_fields
    )
    return res