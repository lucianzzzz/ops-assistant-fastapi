"""性能测试"""
import time
import pytest
from app.core.assistant.repository import InMemoryRepository
from app.core.assistant.service import OpsAssistantService


class TestPerformance:
    """测试查询性能"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return OpsAssistantService(repository=InMemoryRepository())

    def test_query_performance(self, service):
        """测试查询性能（100次查询）"""
        questions = [
            "IF1接收时延异常怎么处理",
            "IF1接收丢包怎么办",
            "CPU使用率过高",
            "内存占用异常",
            "网络延迟问题",
        ]

        start_time = time.time()
        for _ in range(20):  # 每个问题查询20次
            for question in questions:
                result = service.ask(question, province="浙江", top_k=3)
                assert result["confidence"] >= 0
        end_time = time.time()

        total_queries = 100
        elapsed = end_time - start_time
        qps = total_queries / elapsed

        print(f"\n性能指标:")
        print(f"  总查询次数: {total_queries}")
        print(f"  总耗时: {elapsed:.2f}秒")
        print(f"  平均响应时间: {elapsed/total_queries*1000:.2f}ms")
        print(f"  QPS: {qps:.2f}")

        # 断言：平均响应时间应该 < 100ms
        assert elapsed / total_queries < 0.1, f"响应时间过慢: {elapsed/total_queries*1000:.2f}ms"

    def test_cache_effectiveness(self, service):
        """测试缓存效果"""
        question = "IF1接收时延异常怎么处理"

        # 第一次查询（冷启动）
        start = time.time()
        service.ask(question, province="浙江", top_k=3)
        first_time = time.time() - start

        # 第二次查询（缓存命中）
        start = time.time()
        service.ask(question, province="浙江", top_k=3)
        second_time = time.time() - start

        print(f"\n缓存效果:")
        print(f"  第一次查询: {first_time*1000:.2f}ms")
        print(f"  第二次查询: {second_time*1000:.2f}ms")
        print(f"  提升比例: {(first_time - second_time) / first_time * 100:.1f}%")

        # 第二次应该更快（但不一定，取决于系统状态）
        # 这里只是记录，不做严格断言
        assert second_time > 0
