"""
文档处理器模块
负责加载、解析和分块处理各类文档
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import settings


class DocumentProcessor:
    """文档处理器：加载文档并进行分块处理"""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def load_document(self, file_path: str) -> str:
        """加载单个文档，返回文本内容"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix == ".txt":
            return self._load_txt(file_path)
        elif suffix == ".pdf":
            return self._load_pdf(file_path)
        elif suffix == ".docx":
            return self._load_docx(file_path)
        elif suffix == ".md":
            return self._load_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")

    def _load_txt(self, file_path: Path) -> str:
        """加载TXT文件"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _load_pdf(self, file_path: Path) -> str:
        """加载PDF文件"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            return "\n".join(text)
        except ImportError:
            raise ImportError("请安装pypdf库: pip install pypdf")

    def _load_docx(self, file_path: Path) -> str:
        """加载DOCX文件"""
        try:
            from docx import Document
            doc = Document(str(file_path))
            text = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(text)
        except ImportError:
            raise ImportError("请安装python-docx库: pip install python-docx")

    def split_text(self, text: str) -> List[str]:
        """将文本分块，返回分块列表"""
        # 先按段落分割
        paragraphs = re.split(r'\n\s*\n', text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果段落本身就超过 chunk_size，需要进一步拆分
            if len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                # 按句子拆分长段落
                sentences = re.split(r'([。！？\n.!?])', para)
                temp = ""
                for i in range(0, len(sentences) - 1, 2):
                    sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
                    if len(temp) + len(sentence) > self.chunk_size:
                        if temp:
                            chunks.append(temp.strip())
                        temp = sentence
                    else:
                        temp += sentence
                if temp:
                    chunks.append(temp.strip())
                continue

            # 正常情况：将段落加入当前块
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # 重叠：保留当前块的后半部分
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + "\n" + para
            else:
                if current_chunk:
                    current_chunk += "\n" + para
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def process_document(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """处理单个文档：加载并分块，返回带元数据的分块列表"""
        text = self.load_document(file_path)
        chunks = self.split_text(text)

        file_name = Path(file_path).name
        if metadata is None:
            metadata = {}
        metadata["source"] = file_name

        results = []
        for i, chunk in enumerate(chunks):
            if len(chunk) < 10:  # 过滤过短的块
                continue
            results.append({
                "text": chunk,
                "metadata": {**metadata, "chunk_id": i, "chunk_total": len(chunks)}
            })

        return results

    def process_directory(self, dir_path: str, file_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """批量处理目录中的所有文档"""
        dir_path = Path(dir_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {dir_path}")

        all_chunks = []
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in settings.SUPPORTED_FILE_TYPES:
                if file_pattern and file_pattern not in file_path.name:
                    continue
                try:
                    chunks = self.process_document(str(file_path))
                    all_chunks.extend(chunks)
                    print(f"  ✓ 已处理: {file_path.name} → {len(chunks)} 个分块")
                except Exception as e:
                    print(f"  ✗ 处理失败: {file_path.name} - {e}")

        return all_chunks


# 全局实例
document_processor = DocumentProcessor()
