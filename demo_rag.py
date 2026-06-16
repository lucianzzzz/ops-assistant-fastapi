#!/usr/bin/env python3
"""
RAG 系统演示脚本

演示向量检索、RAG 增强和结构化输出的效果
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.enhanced_service import EnhancedOpsAssistantService
from app.core.ai.vector_retriever import VectorRetriever
from app.core.ai.rag_assistant import RAGAssistant


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result: dict):
    """打印查询结果"""
    print(f"\n📝 问题: {result['question']}")
    print(f"🔍 检索方法: {result['retrieval_method']}")
    print(f"📊 置信度: {result['confidence']:.2%}")
    print(f"🔑 关键词: {', '.join(result['keywords'][:5])}")

    print(f"\n📚 匹配知识 ({len(result['matched_knowledge'])} 条):")
    for i, km in enumerate(result['matched_knowledge'][:3], 1):
        print(f"  {i}. {km['question']} (相似度: {km['score']:.2%})")
        if km.get('reason'):
            print(f"     原因: {km['reason']}")

    print(f"\n💡 可能原因:")
    for reason in result['possible_reason'][:3]:
        print(f"  - {reason}")

    print(f"\n🔧 排查步骤:")
    for i, step in enumerate(result['suggested_steps'][:3], 1):
        print(f"  {i}. {step}")


async def demo_vector_search():
    """演示向量检索"""
    print_section("演示 1: 向量检索 vs 字符串匹配")

    # 初始化
    repo = InMemoryRepository()

    # 测试问题（使用同义词）
    questions = [
        "CPU 占用率过高",
        "处理器使用率很高",  # 同义词
        "服务器 CPU 负载过大",  # 语义相似
    ]

    print("\n🔹 字符串匹配结果:")
    service_string = EnhancedOpsAssistantService(
        repository=repo,
        use_vector_search=False,
        action_generator=None
    )

    for q in questions:
        result = service_string.ask(q, top_k=3)
        matches = len(result['matched_knowledge'])
        print(f"  '{q}' -> {matches} 条匹配")

    print("\n🔹 向量检索结果:")
    service_vector = EnhancedOpsAssistantService(
        repository=repo,
        use_vector_search=True,
        action_generator=None
    )

    for q in questions:
        result = service_vector.ask(q, top_k=3)
        matches = len(result['matched_knowledge'])
        print(f"  '{q}' -> {matches} 条匹配")
        if matches > 0:
            print(f"    最佳匹配: {result['matched_knowledge'][0]['question']} ({result['matched_knowledge'][0]['score']:.2%})")


async def demo_rag_enhancement():
    """演示 RAG 增强"""
    print_section("演示 2: RAG AI 增强（需要 OPENAI_API_KEY）")

    repo = InMemoryRepository()
    service = EnhancedOpsAssistantService(
        repository=repo,
        use_vector_search=True,
        action_generator=None
    )

    # 测试一个常见问题（高置信度，不触发 AI）
    print("\n🔹 场景 1: 高置信度查询（不使用 AI）")
    result = await service.ask_with_ai("网管未扫描添加所有服务器", top_k=3)
    print(f"  置信度: {result['confidence']:.2%}")
    print(f"  是否使用 AI: {result.get('ai_fallback', {}).get('used', False)}")

    # 测试一个不常见问题（低置信度，触发 AI）
    print("\n🔹 场景 2: 低置信度查询（使用 RAG AI）")
    result = await service.ask_with_ai("系统响应很慢是什么原因？", top_k=3)
    print(f"  置信度: {result['confidence']:.2%}")

    ai_fallback = result.get('ai_fallback', {})
    if ai_fallback.get('used'):
        print(f"  ✅ 使用了 RAG AI")
        print(f"  📚 AI 有上下文: {ai_fallback.get('with_context', False)}")
        print(f"\n  AI 生成的原因:")
        for reason in result['possible_reason'][:3]:
            print(f"    - {reason}")
    else:
        print(f"  ❌ 未使用 AI (可能未配置 OPENAI_API_KEY)")


async def demo_structured_output():
    """演示结构化输出"""
    print_section("演示 3: 结构化输出")

    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  需要配置 OPENAI_API_KEY 才能演示此功能")
        return

    assistant = RAGAssistant(use_structured_output=True)

    context = [
        {
            "question": "CPU 占用率过高",
            "reason": "某个进程占用过多资源",
            "method": "1. 使用 top 命令查看进程；2. 重启异常进程；3. 优化程序代码",
            "score": 0.85
        }
    ]

    print("\n🔹 输入:")
    print(f"  问题: CPU 占用率一直很高怎么办？")
    print(f"  上下文: {len(context)} 条知识库记录")

    result = await assistant.ask_with_context(
        question="CPU 占用率一直很高怎么办？",
        context=context
    )

    print("\n🔹 结构化输出:")
    parsed = result.get('parsed', {})

    print(f"\n  📌 可能原因:")
    for reason in parsed.get('possible_reasons', []):
        print(f"    - {reason}")

    print(f"\n  🔧 排查步骤:")
    for i, step in enumerate(parsed.get('suggested_steps', []), 1):
        print(f"    {i}. {step}")

    print(f"\n  ⚡ 后续动作:")
    for action in parsed.get('next_actions', []):
        print(f"    - {action}")

    print(f"\n  📊 AI 置信度: {parsed.get('confidence', 'unknown')}")


async def main():
    """主函数"""
    print("\n" + "🚀 " * 20)
    print("  RAG 系统功能演示")
    print("🚀 " * 20)

    # 检查环境
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    print(f"\n📋 环境检查:")
    print(f"  OPENAI_API_KEY: {'✅ 已配置' if has_api_key else '❌ 未配置'}")

    if not has_api_key:
        print("\n⚠️  提示: 未检测到 OPENAI_API_KEY，部分演示将跳过")
        print("   请在 .env 文件中配置 OPENAI_API_KEY 以体验完整功能")

    try:
        # 演示 1: 向量检索
        await demo_vector_search()

        # 演示 2: RAG 增强
        if has_api_key:
            await demo_rag_enhancement()
        else:
            print_section("演示 2: RAG AI 增强（跳过）")
            print("\n⚠️  需要配置 OPENAI_API_KEY")

        # 演示 3: 结构化输出
        if has_api_key:
            await demo_structured_output()
        else:
            print_section("演示 3: 结构化输出（跳过）")
            print("\n⚠️  需要配置 OPENAI_API_KEY")

    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "✨ " * 20)
    print("  演示完成！")
    print("✨ " * 20 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
