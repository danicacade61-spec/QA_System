"""
服务模块
提供知识库管理等高级业务逻辑
"""
# 注意：knowledge_base 使用延迟加载，避免在导入时触发 vector_store 和 rag_engine 的初始化
from typing import Any


def __getattr__(name: str) -> Any:
    if name == "knowledge_base":
        from app.services.knowledge_base import knowledge_base
        return knowledge_base
    raise AttributeError(f"module 'app.services' has no attribute '{name}'")
