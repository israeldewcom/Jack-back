#!/usr/bin/env python3
"""
Quick codebase summary for Render build logs.
Lists all Python files and their first few lines.
"""

import os
import sys
from pathlib import Path

def should_ignore(path):
    """Ignore common directories that don't contain source code."""
    ignore_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules', '.pytest_cache', '.mypy_cache'}
    return any(part in ignore_dirs for part in path.parts)

def print_file_summary(file_path):
    """Print file path and its first non-empty, non-comment line or docstring."""
    print(f"\n📄 {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    lines.append(line.rstrip())
                    if len(lines) >= 3:  # show first 3 meaningful lines
                        break
            if lines:
                for l in lines:
                    print(f"   {l}")
            else:
                print("   (empty or comment-only file)")
    except Exception as e:
        print(f"   ⚠️  Could not read: {e}")

def main():
    root = Path(__file__).parent.parent  # go up one level from scripts/
    print("🔍 CITP Codebase Summary")
    print("=" * 60)
    for py_file in sorted(root.rglob("*.py")):
        if not should_ignore(py_file):
            print_file_summary(py_file.relative_to(root))
    print("=" * 60)
    print("✅ Summary complete.")

if __name__ == "__main__":
    main()
