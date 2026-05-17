"""Test all module imports"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Write results to file instead of stdout to avoid GBK encoding issues
results = []
results.append("=" * 60)
results.append("Module Import Test")
results.append("=" * 60)

tests = [
    ("app.core.config", "from app.core.config import settings"),
    ("app.core.document_processor", "from app.core.document_processor import document_processor"),
    ("app.core.embedding_manager", "from app.core.embedding_manager import embedding_manager"),
    ("app.core.vector_store", "from app.core.vector_store import vector_store"),
    ("app.core.llm_client", "from app.core.llm_client import create_llm_client"),
    ("app.core.rag_engine", "from app.core.rag_engine import rag_engine"),
    ("app.services.knowledge_base", "from app.services.knowledge_base import knowledge_base"),
    ("app.utils.evaluator", "from app.utils.evaluator import QAEvaluator"),
    ("app.api.server", "from app.api.server import app"),
    ("app.ui.app (via import)", "import importlib; importlib.import_module('app.ui.app')"),

]

all_passed = True
for name, imp in tests:
    try:
        exec(imp)
        results.append(f"  [OK] {name}")
    except Exception as e:
        results.append(f"  [FAIL] {name}: {e}")
        all_passed = False

try:
    import main
    results.append(f"  [OK] main (main.py)")
except Exception as e:
    results.append(f"  [FAIL] main (main.py): {e}")
    all_passed = False

results.append("")
if all_passed:
    results.append("All modules imported successfully!")
else:
    results.append("Some modules failed to import. Check errors above.")
results.append("=" * 60)

output_path = os.path.join(project_root, "test_output.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"Test results written to {output_path}")
print(f"Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
