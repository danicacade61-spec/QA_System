# 🤖 基于大语言模型的智能问答系统

## 📋 项目简介

本项目是《自然语言处理》课程设计，实现了一个基于**检索增强生成（RAG）**架构的大语言模型智能问答系统。系统支持知识库构建、智能检索、大模型生成回答等完整流程，提供API服务和交互式Web界面。

### 核心特性

- **RAG架构**：结合向量检索与大语言模型生成，实现高质量的智能问答
- **知识库管理**：支持上传和管理文档，自动分块和向量化
- **多模型支持**：支持OpenAI API、智谱API、本地模型等多种LLM后端
- **完整的评估体系**：支持自动指标（F1、ROUGE-L）和人工评估
- **两种交互方式**：提供RESTful API和Streamlit Web界面

## 🏗️ 系统架构

```
用户提问 → 文档检索（向量相似度搜索）→ 上下文构建 → LLM生成回答
                ↑
          知识库（文档分块 + 向量化）
```

### 项目结构

```
QA_System/
├── main.py                    # 主入口，支持CLI、API、UI三种模式
├── requirements.txt           # 项目依赖
├── README.md                  # 项目说明文档
├── app/
│   ├── __init__.py
│   ├── core/                  # 核心模块
│   │   ├── config.py          # 系统配置
│   │   ├── document_processor.py  # 文档处理与分块
│   │   ├── embedding_manager.py   # 嵌入向量管理
│   │   ├── vector_store.py    # 向量数据库（FAISS）
│   │   ├── llm_client.py      # 大语言模型客户端
│   │   └── rag_engine.py      # RAG引擎核心
│   ├── api/
│   │   └── server.py          # FastAPI RESTful API
│   ├── services/
│   │   └── knowledge_base.py  # 知识库管理
│   ├── ui/
│   │   └── app.py             # Streamlit前端界面
│   └── utils/
│       └── evaluator.py       # 测试评估模块
├── test_data/
│   └── sample_questions.json  # 示例测试数据
├── knowledge_base/            # 知识库存储目录
└── eval_results/              # 评估结果保存目录
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 推荐使用Python 3.10+
python --version

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥

在 `app/core/config.py` 中配置或设置环境变量：

```bash
# 方式一：环境变量（推荐）
export LLM_API_KEY="your-api-key"
export LLM_API_BASE="https://api.openai.com/v1"
export LLM_MODEL_NAME="gpt-3.5-turbo"

# 方式二：直接修改 config.py 中的默认值
```

### 3. 运行系统

#### 启动API服务器

```bash
python main.py --api
# 访问 http://localhost:8000/docs 查看API文档
```

#### 启动Web界面

```bash
python main.py --ui
# 访问 http://localhost:8501 使用交互界面
```

#### 命令行查询

```bash
python main.py --query "什么是Transformer架构？"
```

### 4. 构建知识库

将文档放入目录后，执行：

```bash
# 通过命令行
python main.py --build-kb ./your_documents

# 或通过Web界面上传文档
# 启动UI后，在"知识库管理"标签页上传
```

支持的文档格式：`.txt`, `.pdf`, `.docx`, `.md`

### 5. 运行评估

```bash
# 确保 test_data/ 目录下有测试数据
python main.py --eval
```

## 📚 API文档

启动API服务器后，访问 `http://localhost:8000/docs` 查看完整API文档。

### 主要端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/query` | POST | 问答查询 |
| `/api/query/stream` | POST | 流式问答 |
| `/api/chat/clear` | POST | 清空对话历史 |
| `/api/knowledge-base/stats` | GET | 知识库统计 |
| `/api/knowledge-base/upload` | POST | 上传文档 |
| `/api/knowledge-base/document/{name}` | DELETE | 删除文档 |
| `/api/knowledge-base/clear` | POST | 清空知识库 |

## 🧪 评估方法

### 自动评估指标

| 指标 | 说明 |
|------|------|
| **Exact Match** | 精确匹配率 |
| **Token F1** | 基于Token的F1分数 |
| **ROUGE-L** | 最长公共子序列重合度 |
| **Response Time** | 响应时间 |
| **Retrieval Rate** | 检索覆盖率 |

### 人工评估维度（1-5分）

| 维度 | 说明 |
|------|------|
| **准确性** | 回答是否正确 |
| **相关性** | 回答是否切题 |
| **流畅性** | 回答是否自然通顺 |

## ⚙️ 配置说明

主要配置项在 `app/core/config.py` 中：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_PROVIDER` | `"openai"` | LLM提供者（openai/zhipu/local） |
| `EMBEDDING_MODEL_NAME` | `"BAAI/bge-small-zh-v1.5"` | 嵌入模型 |
| `CHUNK_SIZE` | `256` | 文本分块大小 |
| `RETRIEVAL_TOP_K` | `5` | 检索返回文档数 |
| `TEMPERATURE` | `0.7` | 生成温度 |

## 📊 测试数据说明

`test_data/sample_questions.json` 包含10个示例问答对，涵盖：
- 事实型问题（Transformer、BERT等概念）
- 常识型问题（什么是词嵌入、微调等）
- 开放型问题（系统评估方法等）

## 📝 参考文献

[1] Vaswani et al. "Attention Is All You Need." NeurIPS 2017.
[2] Lewis et al. "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." NeurIPS 2020.
[3] Brown et al. "Language Models are Few-Shot Learners." NeurIPS 2020.
[4] Kamalloo et al. "Evaluating Open-Domain Question Answering in the Era of Large Language Models." ACL 2023.

---

*自然语言处理课程设计 - 基于大语言模型的智能问答方法研究与实现*
