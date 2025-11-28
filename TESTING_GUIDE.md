# 前后端测试指南

## 后端测试

### 启动服务

```bash
cd backend
./start_server.sh
```

或者：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 测试API

```bash
cd backend
python test_backend.py
```

### API端点

- **健康检查**: http://localhost:8000/health
- **API文档**: http://localhost:8000/docs
- **播客列表**: http://localhost:8000/api/podcasts/
- **播客详情**: http://localhost:8000/api/podcasts/{id}
- **播客指标**: http://localhost:8000/api/podcasts/{id}/metrics

### 示例请求

```bash
# 获取播客列表
curl "http://localhost:8000/api/podcasts/?skip=0&limit=10"

# 按分类筛选
curl "http://localhost:8000/api/podcasts/?category=商业&limit=5"

# 获取播客详情
curl "http://localhost:8000/api/podcasts/1"

# 获取播客指标
curl "http://localhost:8000/api/podcasts/1/metrics"
```

## 前端测试

### 打开前端页面

1. 确保后端服务已启动
2. 在浏览器中打开 `frontend/index.html`

或者使用Python简单服务器：

```bash
cd frontend
python -m http.server 8080
```

然后访问: http://localhost:8080

### 前端功能

- ✅ 显示播客列表
- ✅ 按分类筛选
- ✅ 搜索播客
- ✅ 显示统计信息
- ✅ 实时数据加载

## 数据统计

- **播客总数**: 7,202
- **订阅量记录**: 45,730
- **分类数**: 20+

## 注意事项

1. 确保后端服务运行在 http://localhost:8000
2. 如果遇到CORS问题，可以在FastAPI中添加CORS中间件
3. 数据库使用SQLite，位置在 `backend/xyzrank.db`


