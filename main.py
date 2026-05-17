"""
智能问答系统 - 主入口
提供命令行和交互式两种使用方式

Usage:
    python main.py --api         启动API服务器
    python main.py --ui          启动Streamlit前端
    python main.py --query "问题" 单次查询
    python main.py --build-kb    构建知识库
    python main.py --eval        运行评估
"""

import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 延迟导入配置（避免启动时加载LLM和向量库）
def _get_config():
    """延迟获取配置"""
    from app.core.config import settings
    return settings


def _print_banner():
    """打印系统启动横幅"""
    from app.core.config import settings
    print("=" * 55)
    print("  🤖 智能问答系统 - 基于RAG的大语言模型问答")
    print("=" * 55)
    print(f"  © 2026 {settings.COPYRIGHT_OWNER}")
    print(f"  学号: {settings.STUDENT_ID}")
    print(f"  版本: 1.0.0")
    print("=" * 55)

def _get_rag_engine():
    """延迟获取RAG引擎"""
    from app.core.rag_engine import rag_engine
    return rag_engine


def main():
    parser = argparse.ArgumentParser(
        description="智能问答系统 - 基于RAG的大语言模型智能问答",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --api              # 启动API服务
  python main.py --ui               # 启动Web界面
  python main.py --query "什么是Transformer?"  # 命令行查询
  python main.py --build-kb ./docs  # 构建知识库
  python main.py --eval             # 运行测试评估
        """
    )

    parser.add_argument("--api", action="store_true", help="启动FastAPI服务器")
    parser.add_argument("--ui", action="store_true", help="启动Streamlit前端界面")
    parser.add_argument("--query", type=str, help="执行单次查询")
    parser.add_argument("--build-kb", type=str, help="构建知识库（指定文档目录路径）")
    parser.add_argument("--eval", action="store_true", help="运行评估测试")

    args = parser.parse_args()

    if args.api:
        start_api()
    elif args.ui:
        start_ui()
    elif args.query:
        run_query(args.query)
    elif args.build_kb:
        build_knowledge_base(args.build_kb)
    elif args.eval:
        run_evaluation()
    else:
        parser.print_help()


def start_api():
    """启动API服务器"""
    settings = _get_config()
    print("=" * 50)
    print("🤖 智能问答系统 - API 服务器")
    print("=" * 50)
    print(f"LLM提供者: {settings.LLM_PROVIDER}")
    print(f"嵌入模型: {settings.EMBEDDING_MODEL_NAME}")
    print(f"API地址: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"API文档: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print("=" * 50)

    import uvicorn
    uvicorn.run(
        "app.api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_DEBUG
    )


def start_ui():
    """启动Streamlit前端"""
    settings = _get_config()
    print("=" * 50)
    print("🤖 智能问答系统 - Web 界面")
    print("=" * 50)
    print(f"正在启动Streamlit界面...")

    ui_path = Path(__file__).resolve().parent / "app" / "ui" / "app.py"
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(ui_path),
        "--server.port", str(settings.STREAMLIT_PORT),
        "--server.headless", "true"
    ]

    print(f"运行命令: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nStreamlit 界面已关闭")
    except subprocess.CalledProcessError as e:
        print(f"启动Streamlit失败: {e}")
        sys.exit(1)


def run_query(question: str):
    """命令行单次查询"""
    print(f"\n🧑 问题: {question}\n")
    print("🤖 正在思考...")
    rag_engine = _get_rag_engine()
    result = rag_engine.query(question)
    print(f"\n🤖 回答: {result['answer']}\n")

    if result.get("retrieved_docs"):
        print(f"📄 参考了 {len(result['retrieved_docs'])} 个文档块:")
        for i, doc in enumerate(result["retrieved_docs"][:3]):
            source = doc.get("metadata", {}).get("source", "未知")
            score = doc.get("score", 0)
            print(f"   [{i+1}] 来源: {source} 相似度: {score:.3f}")


def build_knowledge_base(dir_path: str):
    """构建知识库"""
    from app.services.knowledge_base import knowledge_base
    print(f"正在从目录构建知识库: {dir_path}")
    result = knowledge_base.add_document_directory(dir_path)
    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result.get('error', '构建失败')}")


def run_evaluation():
    """运行测试评估"""
    settings = _get_config()
    from app.utils.evaluator import QAEvaluator

    # 检查测试数据是否存在
    test_data_dir = Path(settings.ROOT_DIR) / "test_data"
    test_files = list(test_data_dir.glob("*.json")) + \
                 list(test_data_dir.glob("*.jsonl")) + \
                 list(test_data_dir.glob("*.txt"))

    if not test_files:
        print("⚠️ 未找到测试数据，请先将测试数据放入 test_data/ 目录")
        print("支持的格式: .json, .jsonl, .txt")
        return

    evaluator = QAEvaluator()
    for test_file in test_files:
        print(f"\n加载测试数据: {test_file.name}")
        test_data = evaluator.load_test_data(str(test_file))
        report = evaluator.evaluate_batch(test_data)
        evaluator.print_summary(report)


if __name__ == "__main__":
    main()
