"""
系统配置模块
管理智能问答系统的所有配置参数
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """系统配置类"""

    # 项目根目录
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # ---------- 模型配置 ----------
    # 方案A: 调用API (智谱ChatGLM / OpenAI)
    LLM_PROVIDER: str = "zhipu"  # "openai" | "zhipu" | "local"
    API_KEY: str = os.getenv("LLM_API_KEY", "")
    API_BASE_URL: str = os.getenv("LLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "glm-5.1")

    # 方案B: 本地模型
    LOCAL_MODEL_PATH: str = os.getenv("LOCAL_MODEL_PATH", "")
    LOCAL_MODEL_NAME: str = "Qwen/Qwen2-1.5B-Instruct"

    # ---------- 嵌入模型配置 ----------
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIMENSION: int = 512  # bge-small-zh 的维度
    EMBEDDING_DEVICE: str = "cpu"

    # ---------- 向量数据库配置 ----------
    VECTOR_STORE_PATH: str = str(ROOT_DIR / "knowledge_base" / "vector_store")
    INDEX_FILE: str = "faiss_index.bin"
    ID_MAP_FILE: str = "id_map.json"
    CHUNK_META_FILE: str = "chunk_meta.json"

    # ---------- 文档处理配置 ----------
    CHUNK_SIZE: int = 256  # 文本分块大小（字符数）
    CHUNK_OVERLAP: int = 32  # 文本分块重叠大小
    SUPPORTED_FILE_TYPES: list = [".txt", ".pdf", ".docx", ".md"]

    # ---------- 检索配置 ----------
    RETRIEVAL_TOP_K: int = 5  # 检索返回的最相关文档块数
    RETRIEVAL_SCORE_THRESHOLD: float = 0.3  # 检索相似度阈值

    # ---------- 生成配置 ----------
    MAX_INPUT_TOKENS: int = 2048  # 最大输入token数（含检索到的上下文）
    MAX_OUTPUT_TOKENS: int = 1024  # 最大输出token数
    TEMPERATURE: float = 0.7  # 生成温度
    TOP_P: float = 0.9  # Top-p采样

    # ---------- 服务配置 ----------
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False

    # ---------- 版权信息 ----------
    COPYRIGHT_YEAR: str = "2026"
    COPYRIGHT_OWNER: str = "毛树林"
    STUDENT_ID: str = "2025212413"
    COPYRIGHT_TEXT: str = "© {year} {owner}. All rights reserved."

    # ---------- Streamlit 前端配置 ----------
    STREAMLIT_PORT: int = 8501
    STREAMLIT_TITLE: str = "智能问答系统 - 基于RAG的大语言模型问答"
    STREAMLIT_DESCRIPTION: str = (
        "本系统基于检索增强生成（RAG）架构，结合大语言模型的强大生成能力，"
        "实现对用户问题的智能回答。支持知识库文档管理、多轮对话等功能。"
    )

    # ---------- 评估配置 ----------
    EVAL_RESULTS_DIR: str = str(ROOT_DIR / "eval_results")


settings = Settings()
