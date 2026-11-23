"""使用项目现有 RAG 流程、LLM 和 BGE-M3 执行五项 RAGAS 评估。

在项目根目录运行（Python >= 3.12）：
    uv run --with "ragas==0.4.4" python eval/eval.py
    uv run --with "ragas==0.4.4" python eval/eval.py --limit 1
    uv run python eval/eval.py --metric-retries 2

默认读取本文件同目录的 qa.csv，支持“问题/参考答案”和
“question/ground_truth”两套列名，结果写入同目录的 qa_result.csv。
context 列保存 JSON 字符串数组，保留 reranked_docs 的顺序。
单项评分失败时继续处理其他指标，并仅重试失败项（默认额外重试一次）。
最终仍失败的指标保存为 NaN，表示未得到有效评分，而不是零分。
实际运行需要项目 .env、模型文件和 RAG 依赖服务可用；查询流程仍会
正常调用 MongoDB 保存会话，每道问题使用独立的评估会话。

此处使用 RAGAS 0.4.4 保留的 evaluate 和 LangChain 适配接口，
以复用项目模型，并保留 Answer Correctness 指标的原始定义。
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from queue import Empty
from threading import Lock
from typing import Any
from uuid import uuid4


EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent

# 项目同时使用 mj.*、config.* 和 tool.* 导入，必须加入这两个目录。
for import_path in (PROJECT_ROOT / "mj", PROJECT_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

LOGGER = logging.getLogger(__name__)
METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
)
OUTPUT_COLUMNS = ("question", "context", "answer", "ground_truth", *METRIC_NAMES)


def step1_load_questions(input_path: Path) -> list[dict[str, str]]:
    """步骤一：读取带 BOM 或不带 BOM 的 UTF-8 问答文件并检查必填项。"""
    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = [header.strip() for header in (reader.fieldnames or [])]
        if len(headers) != len(set(headers)):
            raise ValueError("qa.csv 包含重复列名。")
        reader.fieldnames = headers
        if {"问题", "参考答案"}.issubset(headers):
            question_key, reference_key = "问题", "参考答案"
        elif {"question", "ground_truth"}.issubset(headers):
            question_key, reference_key = "question", "ground_truth"
        else:
            raise ValueError(
                "qa.csv 必须包含“问题、参考答案”或“question、ground_truth”两列。"
            )

        questions = []
        for row in reader:
            if None in row:
                raise ValueError(f"qa.csv 第 {reader.line_num} 行字段数超过列头数量。")
            question = (row.get(question_key) or "").strip()
            reference = (row.get(reference_key) or "").strip()
            if not question or not reference:
                raise ValueError(f"qa.csv 第 {reader.line_num} 行的问题或参考答案为空。")
            questions.append({"question": question, "ground_truth": reference})

    if not questions:
        raise ValueError("qa.csv 中没有可评估的问答。")
    return questions


def step2_build_evaluators() -> tuple[Any, Any, list[Any]]:
    """步骤二：复用答案节点的 LLM，并将项目 BGE-M3 适配为 RAGAS 嵌入接口。"""
    from langchain_core.embeddings import Embeddings
    try:
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (
            AnswerCorrectness,
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            '请在项目根目录运行：uv run --with "ragas==0.4.4" python eval/eval.py。'
            '如已安装 RAGAS，请检查其版本及依赖是否兼容。'
        ) from exc

    from mj.query_process.nodes.node_answer_output import get_model_tool

    # 该导入对应 mj/tool/bgem3_embedding_tool.py，与检索节点的导入保持一致，
    # 避免以不同模块名导入同一文件而重复加载模型单例。
    from tool.bgem3_embedding_tool import get_bge3_embedding_vector

    embedding_lock = Lock()

    class BgeM3Embeddings(Embeddings):
        """将项目 BGE-M3 的稠密向量转换为 LangChain 嵌入接口。"""

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            """批量生成稠密向量，并串行访问共享模型以避免并发推理冲突。"""
            if not texts:
                return []
            with embedding_lock:
                vectors = get_bge3_embedding_vector(texts)["dense"]
            if len(vectors) != len(texts):
                raise ValueError("BGE-M3 返回的向量数量与输入文本数量不一致。")
            return [[float(value) for value in vector] for vector in vectors]

        def embed_query(self, text: str) -> list[float]:
            """生成单条文本的稠密向量，供答案相关性等指标计算相似度。"""
            return self.embed_documents([text])[0]

    # 与 NodeAnswerOutput.process() 中的 llm = get_model_tool() 完全一致。
    llm = LangchainLLMWrapper(get_model_tool())
    embeddings = LangchainEmbeddingsWrapper(BgeM3Embeddings())
    metrics = [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
        AnswerCorrectness(llm=llm, embeddings=embeddings),
    ]
    # 强化评分输出的 JSON 转义要求，避免说明文字中的双引号破坏字符串。
    json_instruction = (
        "\nReturn only valid JSON matching the required schema. "
        "Inside string values, prefer single quotation marks when quoting text; "
        'otherwise escape every inner double quotation mark as \\". '
        "Do not include text outside the JSON object."
    )
    for metric in metrics:
        for prompt in metric.get_prompts().values():
            if json_instruction not in prompt.instruction:
                prompt.instruction += json_instruction
    return llm, embeddings, metrics


def collect_streamed_answer(task_queue: Any) -> str:
    """消费已完成查询的任务事件，还原流式回答或直接返回的确认回答。"""
    chunks = []
    final_answer = ""
    while True:
        try:
            event = task_queue.get_nowait()
        except Empty:
            break
        data = event.get("data") or {}
        if event.get("event") == "delta":
            chunks.append(data.get("delta", ""))
        elif event.get("event") == "final" and data.get("answer"):
            final_answer = data["answer"]
    return "".join(chunks) or final_answer


def extract_contexts(state: dict[str, Any]) -> list[str]:
    """仅从最终状态的 reranked_docs 提取正文，保留重排顺序和切片边界。"""
    contexts = []
    for doc in state.get("reranked_docs") or []:
        if not isinstance(doc, Mapping):
            raise TypeError("reranked_docs 中的每个文档必须为字典。")
        content = doc.get("content")
        if content is not None and not isinstance(content, str):
            raise TypeError("reranked_docs 中的 content 必须为字符串。")
        if content and content.strip():
            contexts.append(content)
    return contexts


def step3_run_rag(questions: list[dict[str, str]]) -> list[dict[str, Any]]:
    """步骤三：逐题启动真实查询流程，收集检索上下文和实际生成的回答。"""
    from mj.query_process.main_graph import QueryMainGraphRunner
    from tool.task_utils import get_q, q_dict

    records = []
    for index, question in enumerate(questions, start=1):
        LOGGER.info("RAG 查询 %s/%s：%s", index, len(questions), question["question"])
        task_id = f"ragas-task-{uuid4().hex}"
        initial_state = {
            "task_id": task_id,
            "session_id": f"ragas-session-{uuid4().hex}",
            "message_id": "",
            "original_query": question["question"],
            "answer": "",
            "history": [],
            "item_names": [],
            "rewritten_query": question["question"],
            "embedding_chunks": [],
            "hyde_embedding_chunks": [],
            "web_search_docs": [],
            "rrf_chunks": [],
            "reranked_docs": [],
        }
        task_queue = get_q(task_id)
        try:
            state = QueryMainGraphRunner.create_and_run(initial_state)
            if not isinstance(state, Mapping):
                raise TypeError("QueryMainGraphRunner.create_and_run() 必须返回状态字典。")
            # 优先使用答案节点写回的最终答案，同时兼容仅通过队列输出的版本。
            streamed_answer = collect_streamed_answer(task_queue)
            answer = state.get("answer") or streamed_answer
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError(f"第 {index} 道问题未获得有效的 RAG 回答。")
            contexts = extract_contexts(state)
            if not contexts:
                LOGGER.warning("第 %s 道问题的 reranked_docs 为空。", index)
            records.append({**question, "contexts": contexts, "answer": answer})
        except Exception as exc:
            raise RuntimeError(f"第 {index} 道问题执行 RAG 失败：{question['question']}") from exc
        finally:
            q_dict.pop(task_id, None)
    return records


def step4_evaluate(
    records: list[dict[str, Any]],
    llm: Any,
    embeddings: Any,
    metrics: list[Any],
    timeout: int,
    metric_retries: int = 1,
) -> list[dict[str, float]]:
    """步骤四：计算五项指标，仅重试无效评分，保留成功结果并显式输出失败项。"""
    from ragas import EvaluationDataset, evaluate
    from ragas.run_config import RunConfig

    samples = [
        {
            "user_input": record["question"],
            "retrieved_contexts": record["contexts"],
            "response": record["answer"],
            "reference": record["ground_truth"],
        }
        for record in records
    ]

    def run_evaluation(rows: list[dict[str, Any]], selected_metrics: list[Any]) -> list[dict[str, float]]:
        """执行一批评分并校验返回结构，将单项模型或解析异常交由 RAGAS 标为 NaN。"""
        result = evaluate(
            dataset=EvaluationDataset.from_list(rows),
            metrics=selected_metrics,
            llm=llm,
            embeddings=embeddings,
            run_config=RunConfig(timeout=timeout, max_workers=1, max_retries=2, seed=42),
            # 模型可能输出非法 JSON；单项失败时保存 NaN，避免中断整批任务。
            raise_exceptions=False,
            show_progress=True,
        )
        batch_scores = result.scores
        if len(batch_scores) != len(rows):
            raise ValueError("RAGAS 返回的评分数量与样本数量不一致。")
        expected_names = {metric.name for metric in selected_metrics}
        for index, score in enumerate(batch_scores, start=1):
            missing = expected_names - score.keys()
            if missing:
                raise ValueError(f"评分批次第 {index} 行缺少指标：{', '.join(sorted(missing))}")
        return batch_scores

    scores = run_evaluation(samples, metrics)
    for attempt in range(1, metric_retries + 1):
        for metric in metrics:
            failed_indices = [
                index for index, score in enumerate(scores)
                if not math.isfinite(float(score[metric.name]))
            ]
            if not failed_indices:
                continue
            LOGGER.warning(
                "第 %s/%s 次重试 %s，问题序号：%s。其他成功评分保持不变。",
                attempt, metric_retries, metric.name,
                ", ".join(str(index + 1) for index in failed_indices),
            )
            retried_scores = run_evaluation([samples[index] for index in failed_indices], [metric])
            for index, retry_score in zip(failed_indices, retried_scores, strict=True):
                scores[index][metric.name] = retry_score[metric.name]
    return scores


def step5_write_results(
    records: list[dict[str, Any]], scores: list[dict[str, float]], output_path: Path
) -> None:
    """步骤五：按固定九列导出 UTF-8 BOM CSV，并显式保留不可计算的 NaN 分数。"""
    if len(records) != len(scores):
        raise ValueError("RAG 样本数量与 RAGAS 评分数量不一致，停止导出。")
    rows = []
    for index, (record, score) in enumerate(zip(records, scores, strict=True), start=1):
        row = {
            "question": record["question"],
            "context": json.dumps(record["contexts"], ensure_ascii=False),
            "answer": record["answer"],
            "ground_truth": record["ground_truth"],
        }
        for name in METRIC_NAMES:
            value = float(score[name])
            if not math.isfinite(value):
                LOGGER.warning("第 %s 道问题的 %s 未得到有效分数，输出 NaN。", index, name)
                value = float("nan")
            row[name] = value
        rows.append(row)

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    LOGGER.info("已保存 %s 条评估结果：%s", len(rows), output_path)


def main() -> None:
    """解析命令行参数，依次执行读取问答、适配模型、查询、评估和导出。"""
    parser = argparse.ArgumentParser(description="使用项目 RAG 流程执行五项 RAGAS 评估。")
    parser.add_argument("--limit", type=int, help="仅评估前 N 条，默认评估全部问题。")
    parser.add_argument("--timeout", type=int, default=180, help="每项指标超时秒数，默认 180。")
    parser.add_argument("--metric-retries", type=int, default=1, help="无效评分额外重试次数，默认 1；0 表示不重试。")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit 必须大于 0。")
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0。")
    if args.metric_retries < 0:
        parser.error("--metric-retries 不能小于 0。")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    questions = step1_load_questions(EVAL_DIR / "qa.csv")
    if args.limit is not None:
        questions = questions[:args.limit]
    llm, embeddings, metrics = step2_build_evaluators()
    records = step3_run_rag(questions)
    scores = step4_evaluate(records, llm, embeddings, metrics, args.timeout, args.metric_retries)
    step5_write_results(records, scores, EVAL_DIR / "qa_result.csv")


if __name__ == "__main__":
    main()
