"""
核心模块
包含系统配置、文档处理、向量嵌入、向量存储、LLM客户端和RAG引擎
"""

# 注意：只导入无副作用的模块（config, document_processor 等）
# vector_store 和 rag_engine 会在使用时延迟加载，避免未安装faiss/未配置API密钥时崩溃
from app.core.config import settings
from app.core.document_processor import document_processor
from app.core.embedding_manager import embedding_manager

__all__ = [
    "settings",
    "document_processor",
    "embedding_manager",
]
