#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

try:
    from app.main import app
    print("✅ app.main 导入成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
