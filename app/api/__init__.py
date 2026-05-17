"""
API模块
提供基于FastAPI的RESTful API服务
"""
# 注意：app 使用延迟加载，避免在导入时触发 rag_engine 和 vector_store 的初始化
from typing import Any


def __getattr__(name: str) -> Any:
    if name == "app":
        from app.api.server import app
        return app
    raise AttributeError(f"module 'app.api' has no attribute '{name}'")

__all__ = ["app"]
