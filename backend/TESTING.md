# 本地测试指南

## 前置条件

1. **Python 3.10+** 已安装
2. **MySQL 数据库** 已安装并运行
3. **虚拟环境** 已创建并激活

## 快速测试步骤

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置数据库

创建 `.env` 文件（参考 `.env.example`）：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置你的数据库信息：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DB=xyzrank
```

### 3. 创建数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE xyzrank CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 运行数据库迁移

```bash
# 生成初始迁移文件
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，你应该看到类似输出：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 6. 访问 API 文档

打开浏览器访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 7. 运行测试脚本

在另一个终端运行：

```bash
cd backend
python test_api.py
```

## 手动测试

### 测试健康检查

```bash
curl http://localhost:8000/health
```

### 测试创建播客

```bash
curl -X POST "http://localhost:8000/api/podcasts/" \
  -H "Content-Type: application/json" \
  -d '{
    "xyz_id": "test_001",
    "name": "测试播客",
    "category": "科技",
    "description": "这是一个测试"
  }'
```

### 测试获取播客列表

```bash
curl "http://localhost:8000/api/podcasts/?skip=0&limit=10"
```

### 测试添加指标

```bash
# 先获取播客 ID（假设是 1）
curl -X POST "http://localhost:8000/api/podcasts/1/metrics" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_date": "2024-12-20",
    "subscriber_count": 1000
  }'
```

## 常见问题

### 1. 数据库连接失败

- 检查 MySQL 服务是否运行
- 检查 `.env` 文件中的数据库配置
- 确认数据库用户有足够权限

### 2. 迁移失败

- 确保数据库已创建
- 检查数据库连接配置
- 如果表已存在，可能需要先删除或使用 `alembic upgrade head --sql` 查看 SQL

### 3. 导入错误

- 确保所有依赖已安装：`pip install -r requirements.txt`
- 检查 Python 版本：`python --version`

### 4. 端口被占用

- 更改端口：`uvicorn app.main:app --port 8001`
- 或停止占用 8000 端口的进程

## 下一步

测试通过后，可以：
1. 导入 Excel 数据：`POST /api/imports/excel`
2. 执行数据抓取：`POST /api/scraper/run`
3. 查看抓取历史：`GET /api/scraper/runs`

