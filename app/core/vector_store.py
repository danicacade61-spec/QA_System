"""
向量存储模块
基于FAISS的向量数据库，负责文档向量的存储与检索
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np

from app.core.config import settings


class VectorStore:
    """向量存储：基于FAISS的向量数据库"""

    def __init__(self, store_path: str = None):
        self.store_path = Path(store_path or settings.VECTOR_STORE_PATH)
        self.store_path.mkdir(parents=True, exist_ok=True)

        self._index = None
        self._id_map = {}  # FAISS id -> chunk info
        self._chunk_meta = {}  # chunk_id -> metadata
        self._next_id = 0
        self._dimension = settings.EMBEDDING_DIMENSION

        # 尝试加载已有索引
        self._load_index()

    def _get_embedding_manager(self):
        """延迟获取嵌入管理器"""
        from app.core.embedding_manager import embedding_manager
        return embedding_manager

    def _get_index_path(self) -> Path:
        return self.store_path / settings.INDEX_FILE

    def _get_id_map_path(self) -> Path:
        return self.store_path / settings.ID_MAP_FILE

    def _get_meta_path(self) -> Path:
        return self.store_path / settings.CHUNK_META_FILE

    def _init_index(self):
        """初始化FAISS索引"""
        try:
            import faiss
            emb_mgr = self._get_embedding_manager()
            self._dimension = emb_mgr.dimension
            # 使用内积索引（已归一化的向量，内积等于余弦相似度）
            self._index = faiss.IndexIDMap(
                faiss.IndexFlatIP(self._dimension)
            )
        except ImportError:
            raise ImportError("请安装faiss库: pip install faiss-cpu")

    def _load_index(self):
        """从磁盘加载索引"""
        index_path = self._get_index_path()
        id_map_path = self._get_id_map_path()
        meta_path = self._get_meta_path()

        if index_path.exists() and id_map_path.exists() and meta_path.exists():
            try:
                import faiss
                self._index = faiss.read_index(str(index_path))
                with open(id_map_path, "r", encoding="utf-8") as f:
                    self._id_map = json.load(f)
                with open(meta_path, "r", encoding="utf-8") as f:
                    self._chunk_meta = json.load(f)
                self._next_id = len(self._id_map)
                self._dimension = self._index.d
                print(f"已加载向量索引，共 {len(self._id_map)} 个文档块")
            except Exception as e:
                print(f"加载索引失败，将创建新索引: {e}")
                self._init_index()
        else:
            self._init_index()

    def _save_index(self):
        """将索引保存到磁盘"""
        import faiss
        faiss.write_index(self._index, str(self._get_index_path()))
        with open(self._get_id_map_path(), "w", encoding="utf-8") as f:
            json.dump(self._id_map, f, ensure_ascii=False, indent=2)
        with open(self._get_meta_path(), "w", encoding="utf-8") as f:
            json.dump(self._chunk_meta, f, ensure_ascii=False, indent=2)

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[int]:
        """添加文本到向量存储"""
        if not texts:
            return []

        # 生成向量
        emb_mgr = self._get_embedding_manager()
        embeddings = emb_mgr.encode(texts)
        if embeddings.size == 0:
            return []

        # 确保向量维度匹配
        if embeddings.shape[1] != self._dimension:
            print(f"向量维度不匹配: 期望 {self._dimension}, 实际 {embeddings.shape[1]}")
            return []

        # 准备ID
        ids = np.arange(self._next_id, self._next_id + len(texts)).astype(np.int64)
        self._next_id += len(texts)

        # 添加到索引
        self._index.add_with_ids(embeddings, ids)

        # 记录元数据
        if metadatas is None:
            metadatas = [{} for _ in texts]

        for i, (text, meta) in enumerate(zip(texts, metadatas)):
            idx = int(ids[i])
            self._id_map[str(idx)] = {"text": text[:200] + "..." if len(text) > 200 else text}
            self._chunk_meta[str(idx)] = {
                "text": text,
                "metadata": meta,
                "id": idx
            }

        # 保存
        self._save_index()
        print(f"已添加 {len(texts)} 个文档块到向量库")
        return ids.tolist()

    def similarity_search(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """相似度检索：返回最相似的k个文档块"""
        if k is None:
            k = settings.RETRIEVAL_TOP_K

        if self._index is None or self._index.ntotal == 0:
            return []

        # 编码查询
        emb_mgr = self._get_embedding_manager()
        query_vector = emb_mgr.encode_query(query)
        if query_vector.size == 0:
            return []

        query_vector = query_vector.reshape(1, -1).astype(np.float32)

        # 检索
        scores, indices = self._index.search(query_vector, min(k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if score < settings.RETRIEVAL_SCORE_THRESHOLD:
                continue

            chunk_id = str(idx)
            meta = self._chunk_meta.get(chunk_id, {})
            results.append({
                "id": int(idx),
                "text": meta.get("text", ""),
                "metadata": meta.get("metadata", {}),
                "score": float(score)
            })

        return results

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """获取所有文档块"""
        chunks = []
        for chunk_id, meta in self._chunk_meta.items():
            chunks.append({
                "id": int(chunk_id),
                "text": meta.get("text", ""),
                "metadata": meta.get("metadata", {})
            })
        return chunks

    def delete_chunk(self, chunk_id: int) -> bool:
        """删除指定文档块"""
        chunk_id_str = str(chunk_id)
        if chunk_id_str in self._chunk_meta:
            del self._chunk_meta[chunk_id_str]
            del self._id_map[chunk_id_str]
            # FAISS IndexIDMap不支持删除，需要重建
            self._rebuild_index()
            self._save_index()
            return True
        return False

    def clear(self):
        """清空向量存储"""
        self._init_index()
        self._id_map = {}
        self._chunk_meta = {}
        self._next_id = 0
        self._save_index()
        print("向量库已清空")

    def _rebuild_index(self):
        """重建索引（删除操作后需要重建）"""
        import faiss
        old_index = self._index
        self._init_index()

        texts = []
        ids = []
        for chunk_id_str, meta in self._chunk_meta.items():
            texts.append(meta["text"])
            ids.append(int(chunk_id_str))

        if texts:
            emb_mgr = self._get_embedding_manager()
            embeddings = emb_mgr.encode(texts)
            id_array = np.array(ids, dtype=np.int64)
            self._index.add_with_ids(embeddings, id_array)

    @property
    def count(self) -> int:
        """返回文档块数量"""
        return self._index.ntotal if self._index is not None else 0


# 全局实例（创建时不加载模型和faiss，由__init__延迟初始化）
vector_store = VectorStore()
