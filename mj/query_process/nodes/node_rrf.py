# atguigu/query_process/nodes/node_rrf.py

from mj.query_process.base import NodeBase
from mj.query_process.state import QueryGraphState
from mj.tool.logger import logger
from rich import print as rprint

class NodeRrf(NodeBase):
    """
    节点功能：Reciprocal Rank Fusion
    将多路召回的结果（向量、HyDE、Web）进行加权融合排序。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_rrf"

    def process(self, state: QueryGraphState):
        hyde_embedding_chunks = state.get("hyde_embedding_chunks")
        embedding_chunks = state.get("embedding_chunks")

        embedding_chunks_list = [
            (hyde_embedding_chunks, 1),
            (embedding_chunks, 1)
        ]

        rrf_chunks = {}

        for chunks, weight in embedding_chunks_list:
            for idx, chunk in enumerate(chunks, start=1):
                id = chunk.get("id")
                # 拿到倒排的分数
                score = weight / (idx + 60)
                 # 判断最终列表中是否有当前的数据，如果有，则直接累加分数，如果没有，则添加
                if id in rrf_chunks:
                    rrf_chunks[id]["score"] += score
                else:
                    chunk["score"] = score
                    rrf_chunks[id] = chunk

        rrf_result = sorted(rrf_chunks.values(), key=lambda x: x["score"], reverse=True)[:10]

        rprint(rrf_result)

        return {
            "rrf_chunks": rrf_result
        }


if __name__ == '__main__':
    init_state = {
        "hyde_embedding_chunks": [
            {
                "section_title": "## 交流电压测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618089,
                "section_content": "## 交流电压测量\n\n> 图片总结：图片展示数字万用表测量电压的接线图（红表笔接正极、黑表笔接负极），并附有直流/交流电压及直流电流测量的操作步骤与注意事项。\n\n1. 将功能转盘置于V AC的位置。\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极V端口。\n\n3. 将表笔尖端接触被测物。\n\n4. 显示屏上读取电压值。显示屏显示了精确的小数点，数值和(AC,V等)符号。\n\n在显示屏上读取电压数据。不断重调功能转盘至低交流电压档位获得高分辨率读数。读数由精确的小数点和数值表示。\n\n## 直流电流测量",
                "file_name": "万用表RS-12的使用",
                "score": 0.8468649387359619,
                "source": "local"
            },
            {
                "section_title": "## 直流电流测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618090,
                "section_content": "## 直流电流测量\n\n注意：在10A情况下测量时间不能超过30秒，否则将可能损坏仪表或表笔。\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/eb330b9b1b79716fc9feacd30808b4ed86c395ebaab24c29dec65d68060e10be.jpg)\n\n> 图片总结：图片展示数字万用表测量电压的接线方式：黑表笔接COM，红表笔接V端口，表笔并联被测电路，显示屏读取交流/直流电压值。\n\n1. 将黑色表笔插入负极COM端口。",
                "file_name": "万用表RS-12的使用",
                "score": 0.8370262980461121,
                "source": "local"
            },
            {
                "section_title": "## 电阻测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618093,
                "section_content": "## 电阻测量\n\n警告: 为防触电,测量前应断开电源，把所有电容放电，取出电池和拔掉电线。\n\n1. 将功能转盘置于最高电阻Ω位置\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极Ω端口\n\n3. 把表笔接触被测电路或元件。测试时最好断开电路的一端，以使剩余的电路不会干扰被测电阻数值。\n\n4. 读取显示屏上读数，然后将功能转盘调至最低电阻Ω档位，通常大于实际电阻或预测电阻.读数由精确的小数点和数值表示。",
                "file_name": "万用表RS-12的使用",
                "score": 0.8325291872024536,
                "source": "local"
            },
            {
                "section_title": "## 直流电压测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618087,
                "section_content": "## 直流电压测量\n\n注意：正打开或关闭电源时不要进行此项测量，瞬间的强大电压将损坏仪表。\n\n1. 将功能转盘置于V DC的位置。\n\n2. 将黑色表笔插入负极COM端口，红色表笔插入正极V端口。\n\n3. 将表笔尖端接触被测物,确保极性正确(红色连正极,黑色连负极)。\n\n4. 显示屏上读取电压值。显示屏显示了精确的小数点，数值。若极性颠倒，数值前将显示负号。\n\n## 交流电压测量",
                "file_name": "万用表RS-12的使用",
                "score": 0.8319427967071533,
                "source": "local"
            },
            {
                "section_title": "## 直流电流测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618092,
                "section_content": "## 直流电流测量\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/820246ff8d6f448489eb36a1297e028a8ca8ff17100aecb8aa38d685b069fc19.jpg)\n\n> 图片总结：图片展示数字万用表测量电压的接线图：红黑表笔分别接负载两端，表盘显示1.97V，电路中串联电压表符号“V”和“Load”。\n\n## 电阻测量",
                "file_name": "万用表RS-12的使用",
                "score": 0.8284466862678528,
                "source": "local"
            },
            {
                "section_title": "## 背光灯键（BACKLIGHT）",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618085,
                "section_content": "## 背光灯键（BACKLIGHT）\n\n1. 按下背光灯键开启背光灯。\n\n2. 再次按背光灯键关闭背光灯。\n\n警告：小心触电，高压电流十分危险，应小心操作。\n\n1. 为了节省电池损耗，使用后请将旋钮调至“OFF”档。\n\n2. 若测量过程中显示屏出现“OL”，表明测量值超出所选档位，应改选更高档。\n\n注意:在某些低交直流电压档位内，若表笔与被测物断开，显示屏将出现任意不稳定数值。该现象由高输入灵敏度所致。若接通电路，可读到稳定准确的数值。\n\n## 测量非接触交流电压",
                "file_name": "万用表RS-12的使用",
                "score": 0.8116595149040222,
                "source": "local"
            },
            {
                "section_title": "## 交流电压测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618088,
                "section_content": "## 交流电压测量\n\n警告：谨防触电。\n\n若表笔长度不够不能接触到某些240V用具插座的带电部位，则可能出现插座有电而读到的数值却为0的情况。因此若无电压显示，应检查表笔是否接触到了插座内的金属接口。\n\n注意：正打开或关闭电源时不要进行此项测量，瞬间的强大电压将损坏仪表。\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/84c37b209829d15820d5bbe76bbc98e1bf9eddc58bd9c983fc710cb2747d341b.jpg)",
                "file_name": "万用表RS-12的使用",
                "score": 0.6343047022819519,
                "source": "local"
            },
            {
                "section_title": "## 直流电流测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618091,
                "section_content": "## 直流电流测量\n\n1. 将黑色表笔插入负极COM端口。\n\n2. 测量直流200mA 以下的电流,将功能转盘置于最高DC mA档位，并将红色表笔插入mA端口。\n\n3. 测量直流10A时,将功能转盘置于10A档位，并将红色表笔(10A)端口。\n\n4. 断开被测电路的电源。在你想测量电流的位置打开电路绝缘层。\n\n5. 将黑色表笔接触被测电路的负极，红色表笔接触被测电路正极。\n\n6. 接通电源。\n\n7. 在显示屏上读取读数。进行mA DC测量时,不断重调功能转盘至低mA DC档位获得高分辨率读数.读数由精确的小数点和数值表示。",
                "file_name": "万用表RS-12的使用",
                "score": 0.6303359270095825,
                "source": "local"
            },
            {
                "section_title": "## 电阻测量",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618094,
                "section_content": "## 电阻测量\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/3dce15efe5689c2d8c904dfbbb653eef71ce00b270bd08d47e3b474af2fb68a8.jpg)\n\n> 图片总结：图片展示数字万用表测量电阻的操作步骤及短路蜂鸣、二极管测试方法，强调断电安全与正确接线。\n\n## 短路蜂鸣测试",
                "file_name": "万用表RS-12的使用",
                "score": 0.6209187507629395,
                "source": "local"
            },
            {
                "section_title": "## 二极管测试",
                "item_name": "RSPRORS-12数字万用表",
                "id": 470425363154618096,
                "section_content": "## 二极管测试\n\n1. 将黑色表笔插入负极COM 端口，红色表笔插入正极V端口。\n\n2. 将功能转盘置于 位置。\n\n3. 把表笔与二极管相接触，正向电压将显示400 至 700mV.反向电压显示“ 1”符号.短路时将显示接近 0V，开路时会在两种极性上显示“1”符号。\n\n## 电池测试",
                "file_name": "万用表RS-12的使用",
                "score": 0.6204984188079834,
                "source": "local"
            }
        ],
        "embedding_chunks": [
            {
                "section_title": "![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618069,
                "section_content": "![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)\n\n使用说明书\n\nRS-12\n\n编号: 123-1939\n\n数字万用表\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/16f1ae918c8905b9e4fc1d0c08fe8a9b55c34d69f4c1191f790bf08571419299.jpg)\n\n> 图片总结：图片为RS-12数字万用表的使用说明书封面及安全手册开头，含型号、编号、CE标志及安全警示，提示勿超量程使用。\n\nCE",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.7803154587745667,
                "source": "local"
            },
            {
                "section_title": "![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618068,
                "section_content": "![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)\n\n> 图片总结：图片为RS PRO品牌数字万用表（型号RS-12）的使用说明书封面，含品牌标识、型号、编号及CE认证标志。\n\n使用说明书\n\nRS-12\n\n编号: 123-1939\n\n数字万用表",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.7723022103309631,
                "source": "local"
            },
            {
                "section_title": "## 控制与端口",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618076,
                "section_content": "## 控制与端口\n\n1.LCD液晶显示\n\n2.功能选择转盘\n\n3.10A端口\n\n4.COM端口\n\n5.正极端口\n\n6.数据保持按键\n\n7.背光按键\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/d6946861c4592804bd8d7e75b58029565712d4dc58f855e374bf0fcf370c91dd.jpg)\n\n> 图片总结：该图为数字万用表结构图，标注了LCD显示、功能转盘、测试端口（10A、COM、正极）、数据保持与背光按键，并说明了功能符号含义及安全警示。\n\n## 功能符号指示",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.7684300541877747,
                "source": "local"
            },
            {
                "section_title": "![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618070,
                "section_content": "![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/a6c9fcfb41cfc997c0f88e35c06f34818e7b53d83d92fa3580257172c1c24ec7.jpg)\n\nCE\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/17a896b47789994e2944e1590940a56fff9a93c68fed9b924cd572f4917cf087.jpg)\n\n> 图片总结：该图为RS-12型数字万用表说明书封面及安全手册部分，含仪表外观图、型号编号、CE标志及电压量程等安全使用信息。\n\n## 安全手册",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.7652311325073242,
                "source": "local"
            },
            {
                "section_title": "## 安全标识",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618073,
                "section_content": "## 安全标识\n\nCAUTION 表明此处可能出现危险电压，请避开以免导致仪表的损坏。\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/87ccf38edca64aa36a803d7091a6385340dace221ee3105f93037e3b4285d161.jpg)\n\n> 图片总结：图片为电气安全标识，提示操作需参照说明书，警告存在危险电压，禁止连接500VAC/VDC电路，以防人身伤害或设备损坏。\n\n请勿连接到500VAC或VDC的电路上。",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.7596631050109863,
                "source": "local"
            },
            {
                "section_title": "## 功能符号指示",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618077,
                "section_content": "## 功能符号指示\n\n•))) 蜂鸣指示\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/f5470dcb3ab08b06212db41f4b4b4728bcd0d46a0bafcae45dbee4b840a4ec65.jpg)\n\n> 图片总结：该图展示一款数字万用表的界面标识与功能说明，包括LCD显示、端口布局、按键功能、符号含义（如二极管测试、蜂鸣等）及部分规格参数。\n\n二极管测试指示\n\nµ micro (电流范围)\n\nm milli ( 电压/电流范围)\n\nk kilo (电阻范围)\n\nVDC 直流电压",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.758431077003479,
                "source": "local"
            },
            {
                "section_title": "## 电阻测量",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618094,
                "section_content": "## 电阻测量\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/3dce15efe5689c2d8c904dfbbb653eef71ce00b270bd08d47e3b474af2fb68a8.jpg)\n\n> 图片总结：图片展示数字万用表测量电阻的操作步骤及短路蜂鸣、二极管测试方法，强调断电安全与正确接线。\n\n## 短路蜂鸣测试",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.6472539901733398,
                "source": "local"
            },
            {
                "section_title": "## 安全标识",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618072,
                "section_content": "## 安全标识\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/2ec4f0e7e8b05c73503dc25db1ad0e65b99a06b2dea8d8a9525a1865c75095e0.jpg)\n\n> 图片总结：该图片为安全警示标识，三角形内含感叹号，提示操作需参照说明书，并警告存在危险电压风险，禁止连接500V以上电路。\n\n表明此操作须参照说明书进行。\n\nWARNING 表明此处可能出现危险电压，请避开以免导致死亡或严重伤害。\n\nCAUTION 表明此处可能出现危险电压，请避开以免导致仪表的损坏。",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.6457282900810242,
                "source": "local"
            },
            {
                "section_title": "## 直流电流测量",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618090,
                "section_content": "## 直流电流测量\n\n注意：在10A情况下测量时间不能超过30秒，否则将可能损坏仪表或表笔。\n\n![](http://192.168.99.99:9000/kb-bucket/mj_images/20261113/万用表RS-12的使用/eb330b9b1b79716fc9feacd30808b4ed86c395ebaab24c29dec65d68060e10be.jpg)\n\n> 图片总结：图片展示数字万用表测量电压的接线方式：黑表笔接COM，红表笔接V端口，表笔并联被测电路，显示屏读取交流/直流电压值。\n\n1. 将黑色表笔插入负极COM端口。",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.6448848843574524,
                "source": "local"
            },
            {
                "section_title": "## 操作指导",
                "file_name": "万用表RS-12的使用",
                "id": 470425363154618083,
                "section_content": "## 操作指导\n\n## 数值保持按键HOLD",
                "item_name": "RSPRORS-12数字万用表",
                "score": 0.6429538130760193,
                "source": "local"
            }
        ]
    }
    node = NodeRrf()
    node(init_state)