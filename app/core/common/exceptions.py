"""自定义异常体系"""


class OpsAssistantError(Exception):
    """基础异常类"""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ==================== 业务异常 ====================


class KnowledgeNotFoundError(OpsAssistantError):
    """知识库未找到"""

    def __init__(self, question: str):
        super().__init__(
            message=f"未找到问题 '{question}' 的相关知识",
            code="KNOWLEDGE_NOT_FOUND"
        )


class InvalidProvinceError(OpsAssistantError):
    """无效的省份参数"""

    def __init__(self, province: str):
        super().__init__(
            message=f"无效的省份: {province}",
            code="INVALID_PROVINCE"
        )


class InvalidParameterError(OpsAssistantError):
    """无效的参数"""

    def __init__(self, param_name: str, reason: str):
        super().__init__(
            message=f"参数 '{param_name}' 无效: {reason}",
            code="INVALID_PARAMETER"
        )


# ==================== 外部依赖异常 ====================


class AIServiceError(OpsAssistantError):
    """AI服务异常"""

    def __init__(self, message: str = "AI服务暂时不可用"):
        super().__init__(message=message, code="AI_SERVICE_ERROR")


class DatabaseError(OpsAssistantError):
    """数据库异常"""

    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message=message, code="DATABASE_ERROR")


class DataSourceError(OpsAssistantError):
    """数据源异常"""

    def __init__(self, message: str):
        super().__init__(message=message, code="DATA_SOURCE_ERROR")
