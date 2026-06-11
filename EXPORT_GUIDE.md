# 数据导出接入指南

本文档说明如何从 ngs-oplatform 导出数据并接入到 ops-assistant-fastapi 服务。

## 一、从 ngs-oplatform 导出数据

### 导出位置

在 ngs-oplatform 项目中执行数据导出：

```bash
cd /path/to/ngs-oplatform
python manage.py export_knowledge_base --output /path/to/export
```

### 导出内容

导出命令会生成三个 JSON 文件：

1. **knowledge.json** - 知识库数据
2. **metrics.json** - 指标元数据  
3. **public_tags.json** - 公共标签定义

## 二、验证导出文件

### 检查文件存在

```bash
ls -lh /path/to/export/
# 应该看到：
# knowledge.json
# metrics.json
# public_tags.json
```

### 检查文件格式

```bash
# 验证 JSON 格式正确
jq . /path/to/export/knowledge.json | head
jq . /path/to/export/metrics.json | head
jq . /path/to/export/public_tags.json | head
```

### 查看数据统计

```bash
# 查看记录数
echo "知识库: $(jq 'length' /path/to/export/knowledge.json) 条"
echo "指标: $(jq 'length' /path/to/export/metrics.json) 条"
echo "标签: $(jq 'length' /path/to/export/public_tags.json) 条"
```

## 三、启动 FastAPI 服务

### 方式 1: 使用环境变量

```bash
cd /path/to/ops-assistant-fastapi

# 设置数据目录
export OPS_ASSISTANT_DATA_DIR=/path/to/export

# 启动服务（使用启动脚本）
./start.sh

# 或直接使用 uvicorn
uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8012
```

### 方式 2: 使用 .env 文件

创建 `.env` 文件：

```bash
cd /path/to/ops-assistant-fastapi
cat > .env << EOF
OPS_ASSISTANT_DATA_DIR=/path/to/export
OPS_ASSISTANT_PORT=8012
EOF

# 启动服务
./start.sh
```

### 方式 3: 临时运行

```bash
OPS_ASSISTANT_DATA_DIR=/path/to/export ./start.sh
```

## 四、验证数据加载

### 1. 检查服务启动

```bash
curl http://127.0.0.1:8012/api/v1/health
# 应返回: {"status":"ok"}
```

### 2. 检查数据源状态

```bash
curl http://127.0.0.1:8012/api/v1/data-source/status | jq
```

期望输出：

```json
{
  "data_dir": "/path/to/export",
  "knowledge": {
    "file_name": "knowledge.json",
    "file_path": "/path/to/export/knowledge.json",
    "exists": true,
    "loaded_count": 42
  },
  "metrics": {
    "file_name": "metrics.json",
    "file_path": "/path/to/export/metrics.json",
    "exists": true,
    "loaded_count": 15
  },
  "public_tags": {
    "file_name": "public_tags.json",
    "file_path": "/path/to/export/public_tags.json",
    "exists": true,
    "loaded_count": 8
  }
}
```

### 3. 访问 Web 界面

打开浏览器访问：

```
http://127.0.0.1:8012
```

在"数据源状态"卡片中应该看到：
- ✅ 所有文件状态为"存在"
- ✅ 显示正确的加载数量
- ✅ 显示正确的文件路径

### 4. 测试问答功能

```bash
curl -X POST http://127.0.0.1:8012/api/v1/assistant/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "IF1接收时延异常怎么处理",
    "province": "浙江",
    "top_k": 3
  }' | jq
```

## 五、常见问题排查

### 问题 1: 文件显示"缺失"

**原因：** 文件路径或文件名不正确

**解决：**
```bash
# 检查目录
ls -la $OPS_ASSISTANT_DATA_DIR

# 检查环境变量
echo $OPS_ASSISTANT_DATA_DIR

# 确认文件名匹配
export OPS_ASSISTANT_KNOWLEDGE_FILE=your_knowledge.json
```

### 问题 2: 已加载 0 条

**原因：** JSON 格式错误或字段不匹配

**解决：**
```bash
# 验证 JSON 格式
jq . $OPS_ASSISTANT_DATA_DIR/knowledge.json > /dev/null

# 检查字段是否符合规范（参考 README.md）
jq '.[0]' $OPS_ASSISTANT_DATA_DIR/knowledge.json
```

### 问题 3: 问答返回空结果

**原因：** 知识库数据不足或问题描述不匹配

**解决：**
```bash
# 检查知识库内容
jq '.[] | .问题描述' $OPS_ASSISTANT_DATA_DIR/knowledge.json

# 尝试使用数据中已有的问题描述进行测试
```

### 问题 4: 服务启动失败

**原因：** 端口被占用或依赖未安装

**解决：**
```bash
# 检查端口
lsof -i :8012

# 重新安装依赖
rm .venv/installed
./start.sh

# 或使用其他端口
export OPS_ASSISTANT_PORT=8013
./start.sh
```

## 六、数据更新流程

当 ngs-oplatform 的知识库更新后，重新导出并重启服务：

```bash
# 1. 重新导出数据
cd /path/to/ngs-oplatform
python manage.py export_knowledge_base --output /path/to/export

# 2. 重启 FastAPI 服务
cd /path/to/ops-assistant-fastapi
# 如果使用 ./start.sh 启动，按 Ctrl+C 停止后重新运行
./start.sh

# 3. 验证更新
curl http://127.0.0.1:8012/api/v1/data-source/status | jq '.knowledge.loaded_count'
```

## 七、生产环境部署建议

### 使用 systemd 服务

创建 `/etc/systemd/system/ops-assistant.service`:

```ini
[Unit]
Description=Ops Assistant FastAPI Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/ops-assistant-fastapi
Environment="OPS_ASSISTANT_DATA_DIR=/path/to/export"
Environment="PATH=/path/to/ops-assistant-fastapi/.venv/bin"
ExecStart=/path/to/ops-assistant-fastapi/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8012
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ops-assistant
sudo systemctl start ops-assistant
sudo systemctl status ops-assistant
```

### 使用 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

ENV OPS_ASSISTANT_DATA_DIR=/data

EXPOSE 8012
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012"]
```

构建和运行：

```bash
docker build -t ops-assistant .
docker run -d -p 8012:8012 -v /path/to/export:/data ops-assistant
```

## 八、参考资料

- [README.md](./README.md) - 完整项目文档
- [app/seed/](./app/seed/) - 示例数据文件
- [tests/](./tests/) - 测试用例参考
