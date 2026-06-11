import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api.routes.assistant import router as assistant_router
from app.api.routes.agent import router as agent_router
from app.core.common.config import DATA_DIR, KNOWLEDGE_FILE, METRICS_FILE, PUBLIC_TAGS_FILE, STATIC_DIR, TEMPLATES_DIR
from app.core.common.dependencies import get_repository
from app.core.common.logging import setup_logging
from app.core.common.exceptions import OpsAssistantError
from app.middleware.error_handler import ops_error_handler, validation_error_handler, global_error_handler

# 配置日志
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title="Ops Assistant FastAPI", version="0.1.0")

# 注册异常处理器
app.add_exception_handler(OpsAssistantError, ops_error_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(Exception, global_error_handler)

# 添加 CORS 中间件支持前后端分离
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.include_router(assistant_router)
app.include_router(agent_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Ops Assistant FastAPI 启动成功")
    logger.info(f"数据目录: {DATA_DIR}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Ops Assistant FastAPI 关闭")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # 首屏直接加载数据源状态
    repository = get_repository()
    status = repository.get_data_source_status()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data_dir": str(DATA_DIR),
            "knowledge_file": KNOWLEDGE_FILE,
            "metrics_file": METRICS_FILE,
            "public_tags_file": PUBLIC_TAGS_FILE,
            "data_source_status": status,
        },
    )
