"""
RAG引擎模块
检索增强生成（Retrieval-Augmented Generation）的核心实现
"""

from typing import List, Dict, Any, Optional, Generator

from app.core.config import settings


class RAGEngine:
    """
    RAG引擎：实现检索增强生成的完整流程

    流程：
    1. 接收用户问题
    2. 从向量库检索相关文档
    3. 构建包含上下文信息的提示词
    4. 调用大语言模型生成回答
    """

    def __init__(self, llm_provider: str = None):
        from app.core.llm_client import create_llm_client
        self.llm_client = create_llm_client(llm_provider)
        self.conversation_history: List[Dict[str, str]] = []

    def _get_vector_store(self):
        """延迟获取 vector_store，避免未安装faiss时导入失败"""
        from app.core.vector_store import vector_store
        return vector_store

    def _build_system_prompt(self, contexts: List[Dict[str, Any]]) -> str:
        """
        构建系统提示词
        将检索到的文档上下文整合到系统提示中
        """
        if not contexts:
            return """你是一个智能问答助手。请基于你自己的知识回答用户的问题。
如果不知道答案，请诚实地告诉用户你不确定，不要编造信息。
请用中文回答，回答要简洁、准确、有帮助。"""

        # 构建上下文文本
        context_texts = []
        for i, ctx in enumerate(contexts, 1):
            source = ctx.get("metadata", {}).get("source", "未知来源")
            text = ctx.get("text", "")
            score = ctx.get("score", 0)
            context_texts.append(f"[文档{i}] 来源: {source}\n{text}\n")

        context_str = "\n---\n".join(context_texts)

        system_prompt = f"""你是一个基于知识库的智能问答助手。请根据以下提供的参考文档内容回答用户的问题。

参考文档内容：
{context_str}

回答要求：
1. 优先使用参考文档中的信息回答问题
2. 如果参考文档中有相关信息，请引用相关文档进行回答
3. 如果参考文档中不包含相关信息，请基于你的知识回答，并说明"参考文档中未找到相关信息"
4. 不知道或不确定时，请诚实说明，不要编造信息
5. 请用中文回答，回答要简洁、准确、有条理
6. 如果问题需要多步推理，请逐步分析"""

        return system_prompt

    def query(self, question: str, top_k: int = None) -> Dict[str, Any]:
        """
        处理单个问题查询

        Args:
            question: 用户问题
            top_k: 检索文档数量

        Returns:
            包含答案和检索上下文的字典
        """
        top_k = top_k or settings.RETRIEVAL_TOP_K

        # 1. 检索相关文档
        vector_store = self._get_vector_store()
        retrieved_docs = vector_store.similarity_search(question, k=top_k)

        # 2. 构建系统提示
        system_prompt = self._build_system_prompt(retrieved_docs)

        # 3. 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # 添加历史对话（最多保留最近3轮）
        for msg in self.conversation_history[-6:]:
            messages.append(msg)

        # 添加当前问题
        messages.append({"role": "user", "content": question})

        # 4. 调用LLM生成回答
        answer = self.llm_client.chat(messages)

        # 5. 更新对话历史
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": answer})

        # 限制历史长度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return {
            "question": question,
            "answer": answer,
            "retrieved_docs": retrieved_docs,
            "has_context": len(retrieved_docs) > 0
        }

    def query_stream(self, question: str, top_k: int = None) -> Generator[str, None, None]:
        """
        流式查询（逐词返回结果）
        """
        top_k = top_k or settings.RETRIEVAL_TOP_K

        # 检索相关文档
        vector_store = self._get_vector_store()
        retrieved_docs = vector_store.similarity_search(question, k=top_k)

        # 构建系统提示
        system_prompt = self._build_system_prompt(retrieved_docs)

        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        for msg in self.conversation_history[-6:]:
            messages.append(msg)
        messages.append({"role": "user", "content": question})

        # 流式生成
        full_answer = ""
        for chunk in self.llm_client.chat_stream(messages):
            full_answer += chunk
            yield chunk

        # 更新历史
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": full_answer})

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

    def get_retrieved_context(self, question: str, top_k: int = None) -> List[Dict[str, Any]]:
        """仅检索上下文（不生成回答），用于预览"""
        top_k = top_k or settings.RETRIEVAL_TOP_K
        vector_store = self._get_vector_store()
        return vector_store.similarity_search(question, k=top_k)


# 全局实例
rag_engine = RAGEngine()
