#!/usr/bin/env python3
"""分析哪些 agent 模块是未使用的"""

import os
import re
from pathlib import Path

# 要检查的模块
agent_modules = [
    "react_agent",
    "real_react_agent",
    "planner",
    "adaptive_planner",
    "multi_agent",
    "executor",
    "agent_service",
    "action_generator",
]

# 搜索的目录（排除 agent 目录本身）
search_dirs = [
    "app/api",
    "app/main.py",
    "app/core/assistant",
    "app/core/common",
    "tests",
]

def find_imports(module_name, search_paths):
    """查找模块的导入"""
    imports = []

    for search_path in search_paths:
        if os.path.isfile(search_path):
            files = [search_path]
        else:
            files = list(Path(search_path).rglob("*.py"))

        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()

                    # 查找 import 语句
                    patterns = [
                        rf'from\s+app\.core\.agent\.{module_name}\s+import',
                        rf'from\s+app\.core\.agent\s+import.*{module_name}',
                        rf'import\s+app\.core\.agent\.{module_name}',
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content):
                            imports.append(str(file))
                            break
            except Exception as e:
                pass

    return imports

print("=" * 60)
print("Agent 模块使用情况分析")
print("=" * 60)

unused_modules = []
used_modules = []

for module in agent_modules:
    imports = find_imports(module, search_dirs)

    if imports:
        used_modules.append((module, imports))
        print(f"\n✅ {module}")
        print(f"   被使用在:")
        for imp in imports:
            print(f"   - {imp}")
    else:
        unused_modules.append(module)
        print(f"\n❌ {module}")
        print(f"   未被使用")

print("\n" + "=" * 60)
print("总结")
print("=" * 60)

if unused_modules:
    print(f"\n🗑️  未使用的模块 ({len(unused_modules)}个):")
    for module in unused_modules:
        print(f"  - {module}")
else:
    print("\n✅ 所有模块都被使用")

if used_modules:
    print(f"\n✅ 正在使用的模块 ({len(used_modules)}个):")
    for module, _ in used_modules:
        print(f"  - {module}")

# 检查 tools 和 memory 子目录
print("\n" + "=" * 60)
print("检查子模块")
print("=" * 60)

# 检查 tools
tools_used = find_imports("tools", search_dirs)
if tools_used:
    print(f"\n✅ tools 目录被使用")
    for imp in tools_used[:3]:
        print(f"   - {imp}")
else:
    print(f"\n❌ tools 目录未被使用")

# 检查 memory
memory_used = find_imports("memory", search_dirs)
if memory_used:
    print(f"\n✅ memory 目录被使用")
    for imp in memory_used[:3]:
        print(f"   - {imp}")
else:
    print(f"\n❌ memory 目录未被使用")

print("\n" + "=" * 60)
