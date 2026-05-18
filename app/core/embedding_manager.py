"""
嵌入管理模块
负责文本向量化处理
"""

from typing import List, Optional
import numpy as np
from loguru import logger

from app.core.config import settings


class EmbeddingManager:
    """嵌入管理器：将文本转换为向量表示"""

    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._dimension = settings.EMBEDDING_DIMENSION

    def _load_model(self):
        """加载嵌入模型（延迟加载）"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            import os

            # 设置 HuggingFace 镜像源（解决国内网络问题）
            hf_mirror = os.environ.get("HF_ENDPOINT", "")
            if not hf_mirror:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            logger.info(f"正在加载嵌入模型: {self.model_name} ...")
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"嵌入模型加载完成，向量维度: {self._dimension}")
        except Exception as e:
            logger.warning(f"加载嵌入模型失败: {e}")
            logger.warning("使用简单的词袋模型作为回退方案...")
            self._model = None


    def encode(self, texts: List[str]) -> np.ndarray:
        """将文本列表编码为向量矩阵"""
        if not texts:
            return np.array([])

        self._load_model()

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            return embeddings
        else:
            # 回退方案：简单的词袋+TF向量
            return self._fallback_encode(texts)

    def encode_query(self, query: str) -> np.ndarray:
        """编码单个查询文本"""
        return self.encode([query])[0]

    def _fallback_encode(self, texts: List[str]) -> np.ndarray:
        """回退编码方案（当嵌入模型不可用时）"""
        # 构建简单词汇表
        all_words = set()
        for text in texts:
            # 简单分词（中文按字，英文按空格）
            words = self._simple_tokenize(text)
            all_words.update(words)

        word_to_idx = {w: i for i, w in enumerate(all_words)}
        vocab_size = len(word_to_idx) or 1

        embeddings = np.zeros((len(texts), min(vocab_size, self._dimension)))
        for i, text in enumerate(texts):
            words = self._simple_tokenize(text)
            for w in words:
                if w in word_to_idx:
                    idx = word_to_idx[w] % self._dimension
                    embeddings[i, idx] += 1.0

        # L2归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms

        return embeddings

    def _simple_tokenize(self, text: str) -> List[str]:
        """简单分词（优先使用jieba进行中文分词）"""
        import re
        tokens = []

        # 使用jieba进行中文分词
        try:
            import jieba
            zh_text = re.sub(r'[a-zA-Z0-9]+', ' ', text)
            for word in jieba.cut(zh_text):
                word = word.strip()
                if word and len(word) >= 1:
                    tokens.append(word)
        except ImportError:
            for char in text:
                if '\u4e00' <= char <= '\u9fff':
                    tokens.append(char)

        # 英文单词
        for token in re.findall(r'[a-zA-Z]+', text):
            tokens.append(token.lower())

        return tokens

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        if self._model is not None:
            return self._dimension
        self._load_model()
        return self._dimension


# 全局实例
embedding_manager = EmbeddingManager()
