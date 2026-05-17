"""
知识库管理模块
负责知识库的构建、更新和管理
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import settings


class KnowledgeBase:
    """
    知识库管理器
    管理文档的上传、处理、索引构建等操作
    """

    def __init__(self):
        self.kb_path = Path(settings.VECTOR_STORE_PATH).parent
        self.kb_path.mkdir(parents=True, exist_ok=True)
        self._documents_index = {}  # 文档索引
        self._load_documents_index()

    def _get_document_processor(self):
        """延迟获取文档处理器"""
        from app.core.document_processor import document_processor
        return document_processor

    def _get_vector_store(self):
        """延迟获取向量存储"""
        from app.core.vector_store import vector_store
        return vector_store

    def _get_index_path(self) -> Path:
        return self.kb_path / "documents_index.json"

    def _load_documents_index(self):
        """加载文档索引"""
        index_path = self._get_index_path()
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    self._documents_index = json.load(f)
            except Exception:
                self._documents_index = {}

    def _save_documents_index(self):
        """保存文档索引"""
        with open(self._get_index_path(), "w", encoding="utf-8") as f:
            json.dump(self._documents_index, f, ensure_ascii=False, indent=2)

    def add_document(self, file_path: str) -> Dict[str, Any]:
        """
        添加单个文档到知识库

        Args:
            file_path: 文档路径

        Returns:
            处理结果信息
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}

        if file_path.suffix.lower() not in settings.SUPPORTED_FILE_TYPES:
            return {"success": False, "error": f"不支持的文件类型: {file_path.suffix}"}

        try:
            # 处理文档
            doc_processor = self._get_document_processor()
            chunks = doc_processor.process_document(str(file_path))

            # 提取文本和元数据
            texts = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]

            # 添加到向量存储
            vector_store = self._get_vector_store()
            ids = vector_store.add_texts(texts, metadatas)

            # 更新文档索引
            file_name = file_path.name
            self._documents_index[file_name] = {
                "file_name": file_name,
                "file_path": str(file_path),
                "chunk_count": len(chunks),
                "chunk_ids": ids,
                "status": "indexed"
            }
            self._save_documents_index()

            return {
                "success": True,
                "file_name": file_name,
                "chunk_count": len(chunks),
                "message": f"成功添加文档 '{file_name}'，共 {len(chunks)} 个分块"
            }

        except Exception as e:
            return {"success": False, "error": f"处理文档失败: {str(e)}"}

    def add_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """批量添加文档"""
        results = []
        for file_path in file_paths:
            result = self.add_document(file_path)
            results.append(result)
            print(f"  {'✓' if result['success'] else '✗'} {Path(file_path).name}: {result.get('message', result.get('error', ''))}")
        return results

    def add_document_directory(self, dir_path: str) -> Dict[str, Any]:
        """添加目录中的所有文档"""
        dir_path = Path(dir_path)
        if not dir_path.exists():
            return {"success": False, "error": f"目录不存在: {dir_path}"}

        file_paths = []
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in settings.SUPPORTED_FILE_TYPES:
                file_paths.append(str(file_path))

        if not file_paths:
            return {"success": False, "error": f"目录中未找到支持的文档文件"}

        results = self.add_documents(file_paths)
        success_count = sum(1 for r in results if r["success"])
        total_chunks = sum(
            len(self._documents_index.get(Path(f).name, {}).get("chunk_ids", []))
            for f in file_paths
            if Path(f).name in self._documents_index
        )

        return {
            "success": True,
            "total_files": len(file_paths),
            "success_count": success_count,
            "total_chunks": total_chunks,
            "message": f"成功处理 {success_count}/{len(file_paths)} 个文档，共 {total_chunks} 个分块",
            "details": results
        }

    def remove_document(self, file_name: str) -> bool:
        """删除知识库中的文档"""
        if file_name not in self._documents_index:
            return False

        doc_info = self._documents_index[file_name]
        chunk_ids = doc_info.get("chunk_ids", [])

        # 从向量存储中删除每个分块
        vector_store = self._get_vector_store()
        for chunk_id in chunk_ids:
            vector_store.delete_chunk(chunk_id)

        # 更新文档索引
        del self._documents_index[file_name]
        self._save_documents_index()

        print(f"已删除文档: {file_name}")
        return True

    def list_documents(self) -> List[Dict[str, Any]]:
        """列出知识库中的所有文档"""
        docs = []
        for file_name, info in self._documents_index.items():
            docs.append({
                "file_name": file_name,
                "chunk_count": info.get("chunk_count", 0),
                "status": info.get("status", "unknown")
            })
        return docs

    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        doc_count = len(self._documents_index)
        vector_store = self._get_vector_store()
        chunk_count = vector_store.count

        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "documents": self.list_documents()
        }

    def clear(self):
        """清空知识库"""
        vector_store = self._get_vector_store()
        vector_store.clear()
        self._documents_index = {}
        self._save_documents_index()
        print("知识库已清空")


# 全局实例
knowledge_base = KnowledgeBase()
