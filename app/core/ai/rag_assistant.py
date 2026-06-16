"""RAG Assistant - 真正的检索增强生成"""
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

from app.core.common.logging import get_logger

logger = get_logger(__name__)

# 强制加载 .env 文件
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


class StructuredAnswer(BaseModel):
    """结构化的答案输出"""
    possible_reasons: List[str] = Field(description="可能的原因列表")
    suggested_steps: List[str] = Field(description="建议的排查步骤列表")
    next_actions: List[str] = Field(description="后续动作建议列表")
    confidence: str = Field(description="置信度评估：high/medium/low")


class RAGAssistant:
    """RAG 助手 - 基于检索结果增强 LLM 生成"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_structured_output: bool = True
    ):
        """
        初始化 RAG 助手

        Args:
            api_key: OpenAI API Key
            base_url: API Base URL
            model: 模型名称
            use_structured_output: 是否使用结构化输出
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        self.enabled = bool(self.api_key)
        self.use_structured_output = use_structured_output

        if self.enabled:
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,
            )

            # 根据是否需要结构化输出选择不同的链
            if use_structured_output:
                self.chain = self._build_structured_chain()
            else:
                self.chain = self._build_text_chain()

    def _build_text_chain(self):
        """构建文本输出链（兼容旧版）"""
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

    def _build_structured_chain(self):
        """构建结构化输出链"""
        parser = PydanticOutputParser(pydantic_object=StructuredAnswer)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的运维助手，擅长分析和解决运维问题。

请根据用户问题和提供的知识库上下文，生成结构化的分析结果。

{format_instructions}

要求：
- 每个列表至少包含 1-3 条内容
- 排查步骤要具体、可执行
- 如果知识库上下文中有相关信息，优先使用
- 如果上下文不足，基于你的专业知识补充
"""),
            ("user", """运维问题：{question}

知识库上下文：
{context}

请生成结构化分析。""")
        ])

        return (
            {"question": RunnablePassthrough(), "context": RunnablePassthrough(), "format_instructions": lambda _: parser.get_format_instructions()}
            | prompt
            | self.llm
            | parser
        )

    async def ask(self, question: str) -> Dict[str, Any]:
        """
        简单查询（无上下文）- 向后兼容旧接口

        Args:
            question: 用户问题

        Returns:
            查询结果
        """
        return await self.ask_with_context(question, context=[])

    async def ask_with_context(
        self,
        question: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        基于检索上下文的查询（真正的 RAG）

        Args:
            question: 用户问题
            context: 知识库检索结果列表，每项包含 question/reason/method/score

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
            # 构建上下文字符串
            context_str = self._format_context(context)

            if self.use_structured_output:
                # 结构化输出
                result: StructuredAnswer = await self.chain.ainvoke({
                    "question": question,
                    "context": context_str
                })

                return {
                    "enabled": True,
                    "response": self._format_structured_response(result),
                    "parsed": {
                        "possible_reason": result.possible_reasons,
                        "suggested_steps": result.suggested_steps,
                        "next_actions": result.next_actions,
                        "confidence": result.confidence
                    }
                }
            else:
                # 文本输出（兼容旧版）
                response = await self.chain.ainvoke({"question": question})
                parsed = self._parse_text_response(response)

                return {
                    "enabled": True,
                    "response": response,
                    "parsed": parsed
                }

        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
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

    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        """格式化知识库上下文"""
        if not context:
            return "（无相关知识库记录）"

        lines = []
        for i, item in enumerate(context, 1):
            lines.append(f"知识 {i} (相似度: {item.get('score', 0):.2%}):")
            lines.append(f"  问题: {item.get('question', '')}")
            if item.get('reason'):
                lines.append(f"  原因: {item['reason']}")
            if item.get('method'):
                lines.append(f"  方法: {item['method']}")
            lines.append("")

        return "\n".join(lines)

    def _format_structured_response(self, result: StructuredAnswer) -> str:
        """将结构化结果格式化为文本（用于显示）"""
        lines = [
            "**可能原因：**",
            *[f"- {reason}" for reason in result.possible_reasons],
            "",
            "**排查步骤：**",
            *[f"{i}. {step}" for i, step in enumerate(result.suggested_steps, 1)],
            "",
            "**后续动作：**",
            *[f"- {action}" for action in result.next_actions],
            "",
            f"**置信度：** {result.confidence}"
        ]
        return "\n".join(lines)

    def _parse_text_response(self, response: str) -> Dict[str, List[str]]:
        """
        解析文本响应为结构化数据（兼容旧版）

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
