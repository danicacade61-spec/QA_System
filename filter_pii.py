"""
PII（个人身份信息）过滤工具
扫描项目文件中的个人敏感信息（学号、姓名等）并提供清理功能

Usage:
    python filter_pii.py --check          # 仅检查，报告包含PII的文件
    python filter_pii.py --redact         # 将PII替换为占位符
    python filter_pii.py --check --dir ./src  # 检查指定目录
"""

import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# 需要过滤的PII模式（可根据需要扩展）
PII_PATTERNS: Dict[str, str] = {
    "学号": r"2025212413",
    "姓名": r"毛树林",
}

# 排除的目录和文件
EXCLUDE_DIRS = {".git", "__pycache__", "venv", "env", ".venv", "node_modules"}
EXCLUDE_FILES = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
                 ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".docx",
                 ".pptx", ".xlsx", ".zip", ".tar", ".gz"}

# 占位符
PLACEHOLDER = "***"


def find_files(root_dir: Path, extensions: List[str] = None) -> List[Path]:
    """递归查找需要扫描的文件"""
    files = []
    for item in root_dir.rglob("*"):
        if any(excl in item.parts for excl in EXCLUDE_DIRS):
            continue
        if item.suffix in EXCLUDE_FILES:
            continue
        if item.is_file():
            if extensions is None or item.suffix in extensions:
                files.append(item)
    return files


def scan_file(file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
    """扫描单个文件中的PII，返回匹配详情"""
    matches: Dict[str, List[Tuple[int, str]]] = {}
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return matches

    for label, pattern in PII_PATTERNS.items():
        for m in re.finditer(pattern, content):
            line_no = content[:m.start()].count("\n") + 1
            matches.setdefault(label, []).append((line_no, m.group()))
    return matches


def redact_file(file_path: Path) -> int:
    """替换文件中的PII为占位符，返回替换次数"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return 0

    new_content = content
    count = 0
    for pattern in PII_PATTERNS.values():
        new_content, n = re.subn(pattern, PLACEHOLDER, new_content)
        count += n

    if count > 0:
        file_path.write_text(new_content, encoding="utf-8")
    return count


def main():
    parser = argparse.ArgumentParser(description="PII过滤工具 - 扫描并清理个人敏感信息")
    parser.add_argument("--check", action="store_true", help="检查项目中的PII")
    parser.add_argument("--redact", action="store_true", help="替换PII为占位符")
    parser.add_argument("--dir", type=str, default=".", help="扫描目录（默认当前目录）")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not args.check and not args.redact:
        parser.print_help()
        return

    files = find_files(root, extensions=[".py", ".md", ".json", ".txt", ".html", ".yaml", ".yml"])
    print(f"扫描目录: {root}")
    print(f"扫描文件数: {len(files)}")
    print(f"PII模式: {list(PII_PATTERNS.keys())}")
    print()

    total_matches = 0
    affected_files = 0

    for file_path in sorted(files):
        matches = scan_file(file_path)
        if not matches:
            continue

        affected_files += 1
        total_matches += sum(len(v) for v in matches.values())

        if args.check:
            rel = file_path.relative_to(root)
            print(f"📄 {rel}")
            for label, hits in matches.items():
                for line_no, text in hits:
                    print(f"   [{label}] 第{line_no}行: ...{text}...")

        if args.redact:
            n = redact_file(file_path)
            if n > 0:
                print(f"🔧 已替换 {file_path.relative_to(root)}: {n}处")

    print()
    print(f"总计: {affected_files} 个文件, {total_matches} 处匹配")
    if args.redact:
        print("所有匹配项已被替换为占位符。")
    elif args.check and total_matches > 0:
        print("提示: 使用 --redact 参数替换所有匹配项。")


if __name__ == "__main__":
    main()
