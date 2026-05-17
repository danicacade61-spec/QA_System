"""
Streamlit前端界面
智能问答系统的交互式用户界面
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import json
import time

# 使用延迟加载，避免启动时初始化LLM客户端
from app.core.config import settings


# ---------- 页面配置 ----------

st.set_page_config(
    page_title=settings.STREAMLIT_TITLE,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- 自定义CSS ----------

st.markdown("""
<style>
    /* 主标题样式 */
    .main-title {
        text-align: center;
        padding: 1rem 0;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    /* 对话气泡样式 */
    .user-message {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border-left: 4px solid #2563eb;
    }
    .assistant-message {
        background-color: #f3f4f6;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border-left: 4px solid #10b981;
    }
    .context-box {
        background-color: #fffbeb;
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    /* 指标卡片 */
    .metric-card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #e5e7eb;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #2563eb;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #6b7280;
    }
    /* 侧边栏样式 */
    .sidebar-section {
        padding: 1rem 0;
        border-bottom: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


# ---------- 会话状态初始化 ----------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "use_rag" not in st.session_state:
    st.session_state.use_rag = True

if "top_k" not in st.session_state:
    st.session_state.top_k = settings.RETRIEVAL_TOP_K

if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = None

if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = None


def get_rag_engine():
    """延迟获取RAG引擎实例"""
    if st.session_state.rag_engine is None:
        from app.core.rag_engine import rag_engine
        st.session_state.rag_engine = rag_engine
    return st.session_state.rag_engine


def get_knowledge_base():
    """延迟获取知识库实例"""
    if st.session_state.knowledge_base is None:
        from app.services.knowledge_base import knowledge_base
        st.session_state.knowledge_base = knowledge_base
    return st.session_state.knowledge_base


# ---------- 侧边栏 ----------

with st.sidebar:
    st.markdown("### ⚙️ 系统控制面板")

    # 系统信息
    st.markdown("#### 📊 系统状态")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**LLM提供者:** {settings.LLM_PROVIDER}")
    with col2:
        st.markdown(f"**嵌入模型:** {settings.EMBEDDING_MODEL_NAME.split('/')[-1]}")

    st.divider()

    # 知识库统计
    st.markdown("#### 📚 知识库状态")
    try:
        kb = get_knowledge_base()
        stats = kb.get_statistics()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("文档数", stats["document_count"])
        with col2:
            st.metric("分块数", stats["chunk_count"])
    except Exception as e:
        st.info(f"知识库尚未初始化 ({type(e).__name__})")

    st.divider()

    # 检索参数设置
    st.markdown("#### 🔧 检索设置")
    st.session_state.top_k = st.slider(
        "检索文档数量 (top_k)",
        min_value=1, max_value=10, value=settings.RETRIEVAL_TOP_K,
        help="检索时返回的最相关文档块数量，值越大上下文越丰富但可能引入噪音"
    )
    st.session_state.use_rag = st.toggle(
        "启用RAG检索", value=True,
        help="关闭后仅使用模型自身知识回答，不进行知识库检索"
    )

    st.divider()

    # 对话控制
    st.markdown("#### 💬 对话控制")
    if st.button("🗑️ 清空对话", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        try:
            engine = get_rag_engine()
            engine.clear_history()
        except Exception:
            pass
        st.rerun()

    st.divider()

    # 使用说明
    with st.expander("📖 使用说明"):
        st.markdown("""
        **基本操作：**
        1. 在下方输入框中输入问题
        2. 按回车或点击发送按钮
        3. 系统将检索知识库并生成回答

        **知识库管理：**
        - 支持上传 .txt, .pdf, .docx, .md 文件
        - 上传后自动分块和向量化
        - 可在代码中添加更多文档

        **提示：**
        - 可以上传课程资料作为知识库
        - 系统会优先使用知识库中的信息回答
        """)


# ---------- 主界面 ----------

st.markdown('<div class="main-title">🤖 智能问答系统</div>',
            unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">{settings.STREAMLIT_DESCRIPTION}</div>',
    unsafe_allow_html=True
)

# 选项卡
tab1, tab2, tab3 = st.tabs(["💬 对话", "📚 知识库管理", "🔍 知识库检索预览"])

# ========== Tab 1: 对话 ==========

with tab1:
    # 显示对话历史
    chat_container = st.container()

    with chat_container:
        if not st.session_state.messages:
            # 显示欢迎信息
            st.markdown("""
            <div style="text-align: center; padding: 3rem 1rem; color: #9ca3af;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">👋</div>
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">欢迎使用智能问答系统</div>
                <div style="font-size: 0.9rem;">
                    您可以在下方输入问题，系统将检索知识库并结合大语言模型生成回答。<br>
                    支持多轮对话，系统会记住对话上下文。
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i, msg in enumerate(st.session_state.messages):
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="user-message"><strong>🧑 您:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="assistant-message"><strong>🤖 助手:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                    # 显示检索到的上下文（如果有）
                    if "contexts" in msg and msg["contexts"]:
                        with st.expander("📄 查看检索到的参考文档", expanded=False):
                            for j, ctx in enumerate(msg["contexts"]):
                                source = ctx.get("metadata", {}).get("source", "未知")
                                score = ctx.get("score", 0)
                                st.markdown(
                                    f'<div class="context-box">'
                                    f'<strong>文档 {j+1}</strong> | 来源: {source} | 相似度: {score:.3f}<br>'
                                    f'{ctx.get("text", "")[:300]}...'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )

    # 输入区域
    st.divider()

    # 使用 st.chat_input 作为主要输入方式（Streamlit原生支持）
    user_input = st.chat_input("请输入您的问题...")

    # 处理输入
    if user_input and user_input.strip():
        # 显示用户消息
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 显示加载状态
        with st.spinner("🤔 正在思考..."):
            try:
                engine = get_rag_engine()

                if st.session_state.use_rag:
                    result = engine.query(
                        user_input,
                        top_k=st.session_state.top_k
                    )
                    answer = result["answer"]
                    contexts = result.get("retrieved_docs", [])
                else:
                    # 不使用RAG，直接调用LLM
                    from app.core.llm_client import create_llm_client
                    llm = create_llm_client()
                    messages = [{"role": "user", "content": user_input}]
                    answer = llm.chat(messages)
                    contexts = []

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "contexts": contexts
                })

            except Exception as e:
                error_msg = f"抱歉，系统处理时出现错误: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "contexts": []
                })

        st.rerun()

# ========== Tab 2: 知识库管理 ==========

with tab2:
    st.markdown("### 📚 知识库管理")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 上传文档")
        uploaded_file = st.file_uploader(
            "选择文档文件",
            type=["txt", "pdf", "docx", "md"],
            help=f"支持的文件类型: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
        )

        if uploaded_file is not None:
            # 保存并处理上传的文档
            upload_dir = Path(settings.VECTOR_STORE_PATH).parent / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner(f"正在处理文档: {uploaded_file.name}..."):
                kb = get_knowledge_base()
                result = kb.add_document(str(file_path))

            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result.get("error", "处理失败"))

        st.markdown("#### 批量导入文档目录")
        dir_path = st.text_input(
            "输入文档目录路径",
            placeholder="例如: D:/documents/knowledge"
        )
        if st.button("📂 导入目录", use_container_width=True) and dir_path:
            with st.spinner("正在批量处理文档..."):
                kb = get_knowledge_base()
                result = kb.add_document_directory(dir_path)
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result.get("error", "处理失败"))

    with col2:
        st.markdown("#### 知识库文档列表")
        try:
            kb = get_knowledge_base()
            docs = kb.list_documents()
            if docs:
                for doc in docs:
                    st.markdown(f"""
                    <div style="padding: 0.5rem; margin: 0.3rem 0;
                                background: #f9fafb; border-radius: 6px;
                                border: 1px solid #e5e7eb;">
                        <strong>📄 {doc['file_name']}</strong><br>
                        <span style="color: #6b7280; font-size: 0.85rem;">
                            分块数: {doc['chunk_count']} | 状态: {doc['status']}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                if st.button("🗑️ 清空知识库", type="secondary"):
                    kb.clear()
                    st.success("知识库已清空")
                    st.rerun()
            else:
                st.info("知识库为空，请上传文档")
        except Exception as e:
            st.error(f"获取知识库信息失败: {e}")

# ========== Tab 3: 检索预览 ==========

with tab3:
    st.markdown("### 🔍 知识库检索预览")
    st.markdown("输入查询内容，预览从知识库中检索到的相关文档块")

    preview_query = st.text_input(
        "输入查询文本",
        placeholder="例如: 什么是大语言模型？",
        key="preview_query"
    )

    if preview_query:
        with st.spinner("正在检索..."):
            try:
                engine = get_rag_engine()
                results = engine.get_retrieved_context(
                    preview_query,
                    top_k=st.session_state.top_k
                )
                if results:
                    st.markdown(f"**找到 {len(results)} 个相关文档块:**")
                    for i, r in enumerate(results):
                        source = r.get("metadata", {}).get("source", "未知")
                        score = r.get("score", 0)
                        with st.expander(
                            f"文档 {i+1} | 来源: {source} | 相似度: {score:.4f}",
                            expanded=(i == 0)
                        ):
                            st.markdown(f"```\n{r.get('text', '')}\n```")
                else:
                    st.info("未找到相关文档")
            except Exception as e:
                st.error(f"检索失败: {e}")


# ---------- 页脚 ----------

st.divider()
st.markdown(
    f'<div style="text-align: center; color: #9ca3af; font-size: 0.8rem; padding: 1rem 0;">'
    f'基于RAG架构的大语言模型智能问答系统 | 自然语言处理课程设计 | v1.0.0<br>'
    f'© {getattr(settings, "COPYRIGHT_YEAR", "2026")} '
    f'{getattr(settings, "COPYRIGHT_OWNER", "[请输入您的姓名]")}'
    f'. All rights reserved.'
    f'<br>学号: {getattr(settings, "STUDENT_ID", "")}'
    f'</div>',
    unsafe_allow_html=True
)


# ---------- 主入口 ----------

if __name__ == "__main__":
    pass  # 通过 `streamlit run app/ui/app.py` 启动
