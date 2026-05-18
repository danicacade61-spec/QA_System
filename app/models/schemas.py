"""
Pydantic 数据模型
定义 API 请求与响应的数据结构
"""

from typing import Optional, List
from pydantic import BaseModel
from app.core.config import settings


class QueryRequest(BaseModel):
    """查询请求"""
    question: str
    top_k: Optional[int] = settings.RETRIEVAL_TOP_K
    use_stream: Optional[bool] = False


class QueryResponse(BaseModel):
    """查询响应"""
    question: str
    answer: str
    retrieved_docs: list
    has_context: bool


class ChatHistoryClearResponse(BaseModel):
    """清空历史响应"""
    success: bool
    message: str


class KBStatsResponse(BaseModel):
    """知识库统计响应"""
    document_count: int
    chunk_count: int
    documents: list


class AddDocResponse(BaseModel):
    """添加文档响应"""
    success: bool
    file_name: Optional[str] = None
    chunk_count: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None
