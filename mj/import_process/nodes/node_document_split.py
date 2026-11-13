import json
import re
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

from mj.import_process.base import NodeBase
from mj.import_process.state import ImportGraphState
from mj.tool.json_format_tool import json_format
from mj.tool.logger import logger


class NodeDocumentSplit(NodeBase):
    """
    智能文档的切分
    """
    name = "node_document_split"

    def process(self, state: ImportGraphState ):
        """
        此节点主要作用是来切分文档得到切分后的chunk_list，该chunk_list的组成由：
        {
            "section_title": "段落的标题",
            "file_name": "文件名",
            "content":"切分的该chunk的内容",
            "part": "0代表content是个完整的段落，1/2/3/4...代表content不是一个完整的段落，序号代表是切分的顺序"
        }
        :param state:
        :return:
        """
        # 此处处理入口节点的业务逻辑
        # 一、首先拿到文档的标题和文档的内容，并对换行符做统一处理（因为mac、windows、linux等系统中的md文件的换行符不一样）
        file_name = state.get("file_title")
        md_path = state.get("md_path")

        # 防御性处理
        if not file_name:
            logger.error("文件名不能为空！")
            raise Exception("文件名不能为空！")
        if not md_path:
            logger.error("文件路径不能为空！")
            raise Exception("文件路径不能为空！")
        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("文件路径不存在！")
            raise Exception("文件路径不存在！")
        # 获取到文件内容
        md_content = md_path_obj.read_text(encoding='utf-8').replace("\r\n", "\n").replace("\r", "\n")

        # 二、对文档进行切分，并拿到最终的数据，里面有一些东西需要处理：
        # 1、先将文本按照每行进行切分，然后将章节合并，但是需要注意的是，遇到代码块则需要注意：因为代码块中的 # 大概率是注释，所以不能切分
        line_chunk_list = md_content.split("\n")
        section_chunk_lict = []
        is_block = False # 代码块标识符
        start_flag = None # 代码块开始的标识（因为有两种代码块标识符：``` 和 ~~~ ）
        code_pattern = r"^(`{3,}|~{3,})"  # 代码块开始和结束的正则匹配（里面使用了正则的分组捕获，详细文档了解分组捕获）
        title_pattern = r'^\s*#{1,6}\s+.+' # 文档章节的正则匹配
        title_idx = 0 # 每一个章节标题的下标
        for idx, line_chunk in enumerate(line_chunk_list):
            line_chunk = line_chunk.strip() # 去除两端的空白

            # code_pattern_res = re.compile(code_pattern).match(line_chunk)
            code_pattern_res = re.match(code_pattern, line_chunk)
            if is_block:
                # 在代码块中，则判断当前行是否是代码块结束的行
                if code_pattern_res and start_flag == code_pattern_res.group(1):
                    is_block = False
                    start_flag = None
                else:
                    continue
            else:
                # 不在代码块则 使用正则判断当前是否是章节标题
                pattern_res = re.match(title_pattern, line_chunk)
                if pattern_res:
                    # 是章节标题，则直接将之前的标题和段落直接放到 section_chunk_lict 中：
                    section_content = "\n".join(line_chunk_list[title_idx:idx+1])
                    section_chunk_lict.append({
                        "section_title": line_chunk_list[title_idx],
                        "section_content": section_content,
                        "file_name": file_name,
                    })
                    title_idx = idx
                elif code_pattern_res:
                    is_block = True
                    start_flag = code_pattern_res.group(1)

        # 循环结束之后，需要手动将最后一段内容添加进去
        section_chunk_lict.append({
            "section_title": line_chunk_list[title_idx],
            "section_content": "\n".join(line_chunk_list[title_idx:]),
            "file_name": file_name,
        })
        # 2、切分好的章节如果小于 chunk_size ，则直接放到最终的 final_chunk_list 当中，
        #   如果大于chunk_size：
        #       如果有表格，则完整保存，不做切分，直接放到 final_chunk_size 当中即可，保证语义完整性
        #       如果没有表格，则使用 递归字符文本切分器 对该chunk进行二次切分，然后将切分的chunk保存进入 final_chunk_size 即可

        chunk_size = 300
        final_chunk_list = []
        # 定义字符文本切分器
        spliter = RecursiveCharacterTextSplitter(
            separators=[],
            chunk_size=chunk_size,
            chunk_overlap=50,
            length_function=len,
            add_start_index=True   # 在切分前如果使用加载器，就有metadata，这个字典里面就会添加上每个chunk在内容当中的起始位置，但是在本项目中没有使用
        )

        final_chunk_list = []
        for section_chunk in section_chunk_lict:
            section_content = section_chunk.get("section_content")
            section_title = section_chunk.get("section_title")
            file_name = section_chunk.get("file_name")
            # 去除章节的标题
            real_content = section_content[len(section_title)+2:] if section_content.startswith("#") else section_content
            if len(real_content) <= chunk_size or "<table" in real_content:
                final_chunk_list.append({
                    **section_chunk,
                    "part": 0
                })
            else:
                section_split_list = spliter.split_text(real_content)
                for idx, section_split_chunk in enumerate(section_split_list, start=1):
                    final_chunk_list.append({
                        "section_title": section_title,
                        "section_content": section_title+"\n\n"+section_split_chunk,
                        "file_name": file_name,
                        "part": idx
                    })

        # with open(r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\output\json\document_split_json.json", "w", encoding="utf-8") as f:
        #     f.write(json_format(final_chunk_list))

        return {
            "chunks": final_chunk_list,
            "file_title": file_name,
        }


# 此处进行单元测试
if __name__ == "__main__":
    node_document_split = NodeDocumentSplit()
    init_state = {
        "file_title": "万用表RS-12的使用_new",
        "md_path": r"E:\SZ_AIAgent\260817\project\1-ProprietorThinkTank\mj\test\test_files\test_graph_output\万用表RS-12的使用\万用表RS-12的使用_new.md"
    }
    node_document_split(init_state)