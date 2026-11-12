#这个文件是专门用来封装mongodb操作的文件
#1、获取mongodb连接对象 单例
import time

from bson import ObjectId
from pymongo import MongoClient

from mj.config.config import ConfigMongo

mongo_client = None
def get_mongo_client():
    global mongo_client
    if mongo_client is None:
        mongo_client = MongoClient(ConfigMongo.MONGO_URL)
    return mongo_client


#2、创建获取mongodb的表对象，因为只有拿到表对象才能操作表
mongo_tool = None
def get_mongo_tool():
    global mongo_tool
    if mongo_tool is None:
        #mongo_tool对应就是拿到数据库当中的表（表对象）
        mongo_client = get_mongo_client()
        db = mongo_client[ConfigMongo.MONGO_DB_NAME] #拿到数据库对象
        mongo_tool = db["chat_history"] #拿到表对象
        mongo_tool.create_index([("session_id",1),("ts",-1)])
        #按照session_id升序查找会有索引提升效率，按照session_id升序并且按照时间降序查找会有索引提升效率
    return mongo_tool


#3、封装数据表的操作函数（增删改查）以后mongo表的增删改查分别都是调用各自函数去操作

#历史会话记录的文档格式
# {
#     "session_id": "",
#     "role": "",
#     "text": "",
#     "rewritten_query": "",
#     "item_names": [],
#     "ts": 123
# }
# get_recent_messages 根据session_id获取最近的n条消息
def get_recent_messages(session_id,limit=10):
    mongo_tool = get_mongo_tool()
    result = mongo_tool.find({"session_id": session_id}).sort({"ts":-1}).limit(limit)
    return list(result) #这个函数返回的result其实是一个游标对象，必须自己手动转化为list才能拿到字典列表

# clear_history清空某个session_id的所有消息
def clear_history(session_id):
    mongo_tool = get_mongo_tool()
    mongo_tool.delete_many({"session_id": session_id})


# save_chat_message保存历史记录（根据id决定是添加还是修改） 增改一体化（增和改写一个函数）
def save_chat_message(session_id,role,text,rewritten_query=None,item_names=None,ts=None,message_id=None):
    mongo_tool = get_mongo_tool()
    #如果传递过来的参数当中有id,代表是改
    # 如果没有id代表增
    if message_id is None:
        #没传 增
        res = mongo_tool.insert_one({
            "session_id": session_id, #和id没关系 这个代表是哪个会话
            "role": role,
            "text": text,
            "rewritten_query": rewritten_query,
            "item_names": item_names,
            "ts": ts or time.time(),
        })
        return res.inserted_id #返回新添加的这个记录入库时的id
    else:
        #传了 改
        mongo_tool.update_one({"_id":message_id},{
            "$set":{
                "session_id": session_id,  # 和id没关系 这个代表是哪个会话
                "role": role,
                "text": text,
                "rewritten_query": rewritten_query,
                "item_names": item_names,
                "ts": ts or time.time(),
            }
        })

def update_history_item_names(ids,item_names,rewritten_query):
    mongo_tool = get_mongo_tool()
    mongo_tool.update_many({"_id": {"$in":ids}},{
        "$set":{
            "item_names": item_names,
            "rewritten_query": rewritten_query,
        }
    })

if __name__ == '__main__':
    session_id = "test_001"
    save_chat_message(session_id, "user", "咨询下烫金机。")
    save_chat_message(session_id, "assistant", "您好。请问是哪个型号")
    save_chat_message(session_id, "user", "hak180")
    save_chat_message(session_id, "assistant", "具体有什么问题呢？")

    # save_chat_message(session_id, "user", "哈哈哈哈哈",message_id=ObjectId('6af2e60864e076b65cf6da6d'))

    # clear_history(session_id)






