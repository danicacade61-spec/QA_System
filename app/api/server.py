"""
API服务器模块
基于FastAPI实现的RESTful API，提供智能问答系统的后端服务
"""

import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.schemas import (
    QueryRequest, QueryResponse, ChatHistoryClearResponse,
    KBStatsResponse, AddDocResponse
)


def _get_rag_engine():
    """延迟获取RAG引擎"""
    from app.core.rag_engine import rag_engine
    return rag_engine


def _get_knowledge_base():
    """延迟获取知识库"""
    from app.services.knowledge_base import knowledge_base
    return knowledge_base


# ---------- 创建FastAPI应用 ----------

app = FastAPI(
    title="智能问答系统 API",
    description="基于RAG架构的大语言模型智能问答系统后端服务",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- API路由 ----------

@app.get("/")
async def root():
    """根路径，返回系统状态"""
    return {
        "name": "智能问答系统 API",
        "version": "1.0.0",
        "status": "running",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "copyright": settings.COPYRIGHT_TEXT.format(
            year=settings.COPYRIGHT_YEAR,
            owner=settings.COPYRIGHT_OWNER
        )
    }


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    处理问答查询
    - 接收用户问题
    - 从知识库检索相关文档
    - 调用大语言模型生成回答
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    rag_engine = _get_rag_engine()
    result = rag_engine.query(request.question, top_k=request.top_k)
    return QueryResponse(
        question=result["question"],
        answer=result["answer"],
        retrieved_docs=result["retrieved_docs"],
        has_context=result["has_context"]
    )


@app.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    """
    流式问答查询（返回SSE流）
    使用Server-Sent Events实现流式响应
    """
    from fastapi.responses import StreamingResponse

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    async def generate():
        rag_engine = _get_rag_engine()
        for chunk in rag_engine.query_stream(request.question, top_k=request.top_k):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat/clear", response_model=ChatHistoryClearResponse)
async def clear_chat_history():
    """清空对话历史"""
    rag_engine = _get_rag_engine()
    rag_engine.clear_history()
    return ChatHistoryClearResponse(
        success=True,
        message="对话历史已清空"
    )


# ---------- 知识库管理 API ----------

@app.get("/api/knowledge-base/stats", response_model=KBStatsResponse)
async def get_kb_stats():
    """获取知识库统计信息"""
    knowledge_base = _get_knowledge_base()
    stats = knowledge_base.get_statistics()
    return KBStatsResponse(
        document_count=stats["document_count"],
        chunk_count=stats["chunk_count"],
        documents=stats["documents"]
    )


@app.post("/api/knowledge-base/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档到知识库
    支持的格式: .txt, .pdf, .docx, .md
    """
    # 检查文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}。支持的类型: {settings.SUPPORTED_FILE_TYPES}"
        )

    # 保存文件到临时目录
    upload_dir = Path(settings.VECTOR_STORE_PATH).parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 添加到知识库
    knowledge_base = _get_knowledge_base()
    result = knowledge_base.add_document(str(file_path))

    if result["success"]:
        return AddDocResponse(
            success=True,
            file_name=result["file_name"],
            chunk_count=result["chunk_count"],
            message=result["message"]
        )
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "处理文档失败"))


@app.post("/api/knowledge-base/upload-directory")
async def upload_directory(dir_path: str = Query(..., description="文档目录路径")):
    """上传目录中的所有文档"""
    knowledge_base = _get_knowledge_base()
    result = knowledge_base.add_document_directory(dir_path)

    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "处理目录失败"))


@app.delete("/api/knowledge-base/document/{file_name}")
async def delete_document(file_name: str):
    """删除知识库中的文档"""
    knowledge_base = _get_knowledge_base()
    success = knowledge_base.remove_document(file_name)
    if success:
        return {"success": True, "message": f"文档 '{file_name}' 已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"文档 '{file_name}' 不存在")


@app.post("/api/knowledge-base/clear")
async def clear_knowledge_base():
    """清空知识库"""
    knowledge_base = _get_knowledge_base()
    knowledge_base.clear()
    return {"success": True, "message": "知识库已清空"}


# ---------- 配置管理 API ----------

@app.get("/api/config")
async def get_config():
    """获取当前配置（隐藏敏感信息）"""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "retrieval_top_k": settings.RETRIEVAL_TOP_K,
        "max_input_tokens": settings.MAX_INPUT_TOKENS,
        "max_output_tokens": settings.MAX_OUTPUT_TOKENS,
        "temperature": settings.TEMPERATURE,
        "supported_file_types": settings.SUPPORTED_FILE_TYPES
    }


# ---------- 启动入口 ----------

if __name__ == "__main__":
    import uvicorn
    print(f"启动 API 服务器: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"API 文档: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    uvicorn.run(
        "app.api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_DEBUG
    )
