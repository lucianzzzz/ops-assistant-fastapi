.PHONY: help install test run clean format lint docker-build docker-up docker-down

help:  ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	pip install -e ".[dev]"

test:  ## 运行测试
	pytest -v --cov=app --cov-report=term --cov-report=html

test-fast:  ## 快速测试（无覆盖率）
	pytest -v

run:  ## 启动开发服务器
	uvicorn app.main:app --host 127.0.0.1 --port 8012 --reload

format:  ## 格式化代码
	black app/ tests/
	ruff check --fix app/ tests/

lint:  ## 代码检查
	black --check app/ tests/
	ruff check app/ tests/
	mypy app/

clean:  ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true

docker-build:  ## 构建Docker镜像
	docker-compose build

docker-up:  ## 启动Docker容器
	docker-compose up -d

docker-down:  ## 停止Docker容器
	docker-compose down

docker-logs:  ## 查看容器日志
	docker-compose logs -f
