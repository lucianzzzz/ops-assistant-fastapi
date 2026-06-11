import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 强制加载 .env 文件，覆盖系统环境变量
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


class AIAssistant:
    """AI 助手，当本地知识库匹配度不足时提供 AI 查询"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """
        初始化 AI 助手

        Args:
            api_key: OpenAI API Key，默认从环境变量 OPENAI_API_KEY 读取
            base_url: API Base URL，默认从环境变量 OPENAI_BASE_URL 读取
            model: 模型名称，默认从环境变量 OPENAI_MODEL 读取，如无则使用 gpt-4
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        self.enabled = bool(self.api_key)

        if self.enabled:
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,
            )
            self.chain = self._build_chain()

    def _build_chain(self):
        """构建 LangChain 查询链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的运维助手，擅长分析和解决运维问题。

你的任务是：
1. 分析用户提出的运维问题
2. 提供可能的原因分析
3. 给出详细的排查步骤
4. 建议后续的处理动作

请用专业、清晰、结构化的方式回答。回答格式如下：

**可能原因：**
- 原因1
- 原因2

**排查步骤：**
1. 步骤1
2. 步骤2
3. 步骤3

**后续动作：**
- 动作1
- 动作2

注意：
- 回答要具体、可执行
- 考虑常见的运维场景（网络、服务器、应用、数据库等）
- 如果问题涉及具体指标，要说明如何查看和分析该指标
"""),
            ("user", "运维问题：{question}")
        ])

        return prompt | self.llm | StrOutputParser()

    async def ask(self, question: str) -> dict[str, any]:
        """
        使用 AI 查询运维问题

        Args:
            question: 用户问题

        Returns:
            包含 AI 分析结果的字典
        """
        if not self.enabled:
            return {
                "enabled": False,
                "response": None,
                "parsed": {
                    "possible_reason": ["AI 查询未启用，请配置 OPENAI_API_KEY 环境变量"],
                    "suggested_steps": [],
                    "next_actions": []
                }
            }

        try:
            response = await self.chain.ainvoke({"question": question})
            parsed = self._parse_response(response)

            return {
                "enabled": True,
                "response": response,
                "parsed": parsed
            }
        except Exception as e:
            return {
                "enabled": True,
                "response": None,
                "error": str(e),
                "parsed": {
                    "possible_reason": [f"AI 查询失败: {str(e)}"],
                    "suggested_steps": [],
                    "next_actions": []
                }
            }

    def _parse_response(self, response: str) -> dict[str, list[str]]:
        """
        解析 AI 响应，提取结构化信息

        Args:
            response: AI 的文本响应

        Returns:
            结构化的结果字典
        """
        import re

        result = {
            "possible_reason": [],
            "suggested_steps": [],
            "next_actions": []
        }

        # 提取可能原因
        reason_pattern = r'\*\*可能原因[：:]\*\*\s*(.*?)(?=\*\*排查步骤|\*\*后续动作|$)'
        reason_match = re.search(reason_pattern, response, re.DOTALL)
        if reason_match:
            reasons = re.findall(r'[-•]\s*(.+)', reason_match.group(1))
            result["possible_reason"] = [r.strip() for r in reasons if r.strip()]

        # 提取排查步骤
        steps_pattern = r'\*\*排查步骤[：:]\*\*\s*(.*?)(?=\*\*后续动作|$)'
        steps_match = re.search(steps_pattern, response, re.DOTALL)
        if steps_match:
            steps = re.findall(r'\d+\.\s*(.+)', steps_match.group(1))
            result["suggested_steps"] = [s.strip() for s in steps if s.strip()]

        # 提取后续动作
        actions_pattern = r'\*\*后续动作[：:]\*\*\s*(.*?)$'
        actions_match = re.search(actions_pattern, response, re.DOTALL)
        if actions_match:
            actions = re.findall(r'[-•]\s*(.+)', actions_match.group(1))
            result["next_actions"] = [a.strip() for a in actions if a.strip()]

        # 如果解析失败，将整个响应放到可能原因中
        if not any(result.values()):
            result["possible_reason"] = [response]

        return result
