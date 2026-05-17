"""
工具模块
提供测试评估等工具功能
"""
# 注意：QAEvaluator 使用延迟加载，避免在导入时触发 rag_engine 的初始化
from typing import Any


def __getattr__(name: str) -> Any:
    if name == "QAEvaluator":
        from app.utils.evaluator import QAEvaluator
        return QAEvaluator
    raise AttributeError(f"module 'app.utils' has no attribute '{name}'")
