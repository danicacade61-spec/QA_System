"""
测试评估模块
实现对智能问答系统的功能测试和效果评估
"""

import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np
from loguru import logger

from app.core.config import settings


def _get_rag_engine():
    """延迟获取RAG引擎"""
    from app.core.rag_engine import rag_engine
    return rag_engine


class QAEvaluator:
    """问答系统评估器"""

    def __init__(self, results_dir: str = None):
        self.results_dir = Path(results_dir or settings.EVAL_RESULTS_DIR)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def load_test_data(self, file_path: str) -> List[Dict[str, str]]:
        """
        加载测试数据集
        支持的格式: JSON, JSONL
        每项包含: {"question": "...", "reference_answer": "..."}
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"测试数据文件不存在: {file_path}")

        if file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        elif file_path.suffix == ".jsonl":
            data = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            return data
        elif file_path.suffix == ".txt":
            return self._load_txt_test_data(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    def _load_txt_test_data(self, file_path: Path) -> List[Dict[str, str]]:
        """加载TXT格式的测试数据"""
        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current = {}
        for line in lines:
            line = line.strip()
            if line.startswith("Q:"):
                if current:
                    data.append(current)
                current = {"question": line[2:].strip()}
            elif line.startswith("A:"):
                current["reference_answer"] = line[2:].strip()

        if current:
            data.append(current)
        return data

    def evaluate_single(self, question: str, reference_answer: str = None) -> Dict[str, Any]:
        """评估单个问答对"""
        start_time = time.time()

        # 获取回答
        rag_engine = _get_rag_engine()
        result = rag_engine.query(question)

        elapsed = time.time() - start_time
        generated_answer = result["answer"]
        retrieved_docs = result.get("retrieved_docs", [])

        # 计算评估指标
        metrics = {
            "response_time": round(elapsed, 3),
            "has_retrieved_docs": len(retrieved_docs) > 0,
            "retrieved_count": len(retrieved_docs),
            "answer_length": len(generated_answer),
        }

        # 如果有参考答案，计算自动评估指标
        if reference_answer:
            text_metrics = self._compute_text_metrics(generated_answer, reference_answer)
            metrics.update(text_metrics)

        return {
            "question": question,
            "reference_answer": reference_answer,
            "generated_answer": generated_answer,
            "retrieved_docs": [
                {
                    "source": d.get("metadata", {}).get("source", "未知"),
                    "score": d.get("score", 0),
                    "text_preview": d.get("text", "")[:200]
                }
                for d in retrieved_docs[:3]
            ],
            "metrics": metrics
        }

    def evaluate_batch(self, test_data: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量评估"""
        results = []
        total_start = time.time()

        logger.info(f"开始批量评估，共 {len(test_data)} 个测试样本...")
        for i, item in enumerate(test_data):
            question = item.get("question", "")
            reference = item.get("reference_answer", item.get("answer", ""))

            if not question:
                continue

            logger.info(f"  [{i+1}/{len(test_data)}] 评估: {question[:50]}...")
            result = self.evaluate_single(question, reference or None)
            results.append(result)

        total_elapsed = time.time() - total_start

        # 计算汇总统计
        summary = self._compute_summary(results)

        eval_report = {
            "basic_info": {
                "evaluation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_questions": len(results),
                "total_time_seconds": round(total_elapsed, 2),
                "avg_time_per_question": round(total_elapsed / max(len(results), 1), 3)
            },
            "summary_metrics": summary,
            "detailed_results": results
        }

        # 保存评估报告
        report_path = self._save_report(eval_report)
        eval_report["report_path"] = str(report_path)

        return eval_report

    def _compute_text_metrics(self, generated: str, reference: str) -> Dict[str, float]:
        """计算文本评估指标"""
        metrics = {}

        # 1. 精确匹配 (Exact Match)
        metrics["exact_match"] = 1.0 if generated.strip() == reference.strip() else 0.0

        # 2. 基于Token的F1分数（简化版）
        gen_tokens = set(self._tokenize(generated))
        ref_tokens = set(self._tokenize(reference))

        if ref_tokens:
            intersection = gen_tokens & ref_tokens
            precision = len(intersection) / max(len(gen_tokens), 1)
            recall = len(intersection) / max(len(ref_tokens), 1)
            metrics["token_precision"] = round(precision, 4)
            metrics["token_recall"] = round(recall, 4)
            metrics["token_f1"] = round(
                2 * precision * recall / max(precision + recall, 1e-10), 4
            )
        else:
            metrics["token_precision"] = 0.0
            metrics["token_recall"] = 0.0
            metrics["token_f1"] = 0.0

        # 3. ROUGE-L (最长公共子序列)
        metrics["rouge_l"] = round(self._compute_rouge_l(generated, reference), 4)

        return metrics

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        import re
        tokens = []
        # 英文单词
        for token in re.findall(r'[a-zA-Z0-9]+', text.lower()):
            tokens.append(token)
        # 中文字符
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                tokens.append(char)
        return tokens

    def _compute_rouge_l(self, generated: str, reference: str) -> float:
        """计算ROUGE-L（最长公共子序列）"""
        gen_tokens = self._tokenize(generated)
        ref_tokens = self._tokenize(reference)

        if not ref_tokens:
            return 0.0

        # 计算LCS长度（动态规划）
        m, n = len(gen_tokens), len(ref_tokens)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if gen_tokens[i - 1] == ref_tokens[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        lcs = dp[m][n]
        precision = lcs / max(m, 1)
        recall = lcs / max(n, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-10)

        return f1

    def _compute_summary(self, results: List[Dict]) -> Dict[str, float]:
        """计算评估汇总统计"""
        if not results:
            return {}

        metrics_list = [r.get("metrics", {}) for r in results]

        summary = {}

        # 响应时间
        response_times = [m.get("response_time", 0) for m in metrics_list]
        summary["avg_response_time"] = round(np.mean(response_times), 3)
        summary["max_response_time"] = round(max(response_times), 3)
        summary["min_response_time"] = round(min(response_times), 3)

        # 检索相关
        summary["avg_retrieved_docs"] = round(
            np.mean([m.get("retrieved_count", 0) for m in metrics_list]), 2
        )
        summary["retrieval_rate"] = round(
            np.mean([1.0 if m.get("has_retrieved_docs") else 0.0 for m in metrics_list]), 4
        )

        # 文本指标（如果有参考答案）
        has_reference = [m for m in metrics_list if "token_f1" in m]
        if has_reference:
            summary["avg_token_f1"] = round(
                np.mean([m["token_f1"] for m in has_reference]), 4
            )
            summary["avg_token_precision"] = round(
                np.mean([m["token_precision"] for m in has_reference]), 4
            )
            summary["avg_token_recall"] = round(
                np.mean([m["token_recall"] for m in has_reference]), 4
            )
            summary["avg_rouge_l"] = round(
                np.mean([m["rouge_l"] for m in has_reference]), 4
            )
            summary["exact_match_rate"] = round(
                np.mean([m["exact_match"] for m in has_reference]), 4
            )

        # 平均回答长度
        summary["avg_answer_length"] = round(
            np.mean([m.get("answer_length", 0) for m in metrics_list]), 1
        )

        return summary

    def _save_report(self, report: Dict) -> Path:
        """保存评估报告"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"eval_report_{timestamp}.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 同时保存一份TXT格式的摘要
        summary_path = self.results_dir / f"eval_summary_{timestamp}.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("智能问答系统 - 评估报告摘要\n")
            f.write("=" * 60 + "\n\n")

            info = report.get("basic_info", {})
            f.write(f"评估时间: {info.get('evaluation_time', '')}\n")
            f.write(f"测试样本数: {info.get('total_questions', 0)}\n")
            f.write(f"总耗时: {info.get('total_time_seconds', 0)}秒\n")
            f.write(f"平均响应时间: {info.get('avg_time_per_question', 0)}秒\n\n")

            summary = report.get("summary_metrics", {})
            f.write("-" * 40 + "\n")
            f.write("性能指标:\n")
            f.write("-" * 40 + "\n")
            f.write(f"平均响应时间: {summary.get('avg_response_time', 'N/A')}秒\n")
            f.write(f"平均检索文档数: {summary.get('avg_retrieved_docs', 'N/A')}\n")
            f.write(f"检索覆盖率: {summary.get('retrieval_rate', 'N/A')}\n\n")

            if "avg_token_f1" in summary:
                f.write("-" * 40 + "\n")
                f.write("效果指标:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Token F1: {summary.get('avg_token_f1', 'N/A')}\n")
                f.write(f"Token 精确率: {summary.get('avg_token_precision', 'N/A')}\n")
                f.write(f"Token 召回率: {summary.get('avg_token_recall', 'N/A')}\n")
                f.write(f"ROUGE-L: {summary.get('avg_rouge_l', 'N/A')}\n")
                f.write(f"精确匹配率: {summary.get('exact_match_rate', 'N/A')}\n\n")

            f.write("=" * 60 + "\n")

        logger.info(f"评估报告已保存: {report_path}")
        logger.info(f"评估摘要已保存: {summary_path}")

        return report_path

    def print_summary(self, report: Dict):
        """打印评估摘要"""
        print("\n" + "=" * 60)
        print("📊 智能问答系统 - 评估结果摘要")
        print("=" * 60)

        info = report.get("basic_info", {})
        print(f"\n📋 基本信息:")
        print(f"  测试样本数: {info.get('total_questions', 0)}")
        print(f"  总耗时: {info.get('total_time_seconds', 0)}秒")
        print(f"  平均响应时间: {info.get('avg_time_per_question', 0)}秒")

        summary = report.get("summary_metrics", {})
        print(f"\n⚡ 性能指标:")
        print(f"  平均响应时间: {summary.get('avg_response_time', 'N/A')}秒")
        print(f"  平均检索文档数: {summary.get('avg_retrieved_docs', 'N/A')}")
        retrieval_rate = summary.get('retrieval_rate')
        if retrieval_rate is not None:
            print(f"  检索覆盖率: {retrieval_rate*100:.1f}%")
        else:
            print(f"  检索覆盖率: N/A")

        if "avg_token_f1" in summary:
            print(f"\n🎯 效果指标:")
            print(f"  Token F1: {summary.get('avg_token_f1', 'N/A')}")
            print(f"  Token 精确率: {summary.get('avg_token_precision', 'N/A')}")
            print(f"  Token 召回率: {summary.get('avg_token_recall', 'N/A')}")
            print(f"  ROUGE-L: {summary.get('avg_rouge_l', 'N/A')}")
            exact_match_rate = summary.get('exact_match_rate')
            if exact_match_rate is not None:
                print(f"  精确匹配率: {exact_match_rate*100:.1f}%")
            else:
                print(f"  精确匹配率: N/A")

        print("\n" + "=" * 60 + "\n")
