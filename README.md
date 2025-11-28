# XYZRank - 小宇宙播客排名追踪系统

一个自动化播客数据追踪和排名系统，用于管理小宇宙平台上的播客信息，每日自动抓取订阅者数量等关键指标，并记录历史数据变化趋势。

## 📋 项目概述

XYZRank 是一个基于 FastAPI 的播客数据追踪系统，主要功能包括：

- 🎙️ **播客管理**：创建、查询、更新、删除播客信息
- 📊 **指标追踪**：记录每日订阅者数量等关键指标
- 🤖 **自动抓取**：定时自动抓取播客数据
- 📥 **数据导入**：支持从 Excel 批量导入播客数据
- 📈 **历史分析**：保存每日快照，支持趋势分析

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MySQL 5.7+ 或 8.0+
- Redis（可选，用于缓存）

### 安装步骤

1. **克隆项目**
```bash
cd xyzrank_v6
```

2. **创建虚拟环境**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**

创建 `.env` 文件：
```env
APP_NAME=XYZRank API
ENVIRONMENT=development

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=xyzrank
MYSQL_PASSWORD=xyzrank
MYSQL_DB=xyzrank
MYSQL_ECHO=false
```

5. **初始化数据库**

```bash
# 创建数据库迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

6. **启动服务**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 📚 API 文档

### 播客管理

- `GET /api/podcasts/` - 获取播客列表（支持分页和分类筛选）
- `GET /api/podcasts/{id}` - 获取播客详情
- `POST /api/podcasts/` - 创建新播客
- `PATCH /api/podcasts/{id}` - 更新播客信息
- `DELETE /api/podcasts/{id}` - 删除播客
- `GET /api/podcasts/{id}/metrics` - 获取播客指标历史
- `POST /api/podcasts/{id}/metrics` - 添加每日指标

### 数据导入

- `POST /api/imports/excel` - 从 Excel 文件导入播客数据

### 爬虫功能

- `POST /api/scraper/run` - 执行批量抓取任务
- `POST /api/scraper/podcast/{id}` - 抓取单个播客数据
- `GET /api/scraper/runs` - 获取抓取任务历史

### 系统

- `GET /health` - 健康检查
- `GET /` - 服务元信息

详细的 API 文档可以在启动服务后访问 `/docs` 查看。

## 📖 使用示例

### 1. 导入 Excel 数据

```bash
curl -X POST "http://localhost:8000/api/imports/excel" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@小宇宙专辑资料-all.xlsx" \
  -F "skip_existing=true"
```

### 2. 创建播客

```bash
curl -X POST "http://localhost:8000/api/podcasts/" \
  -H "Content-Type: application/json" \
  -d '{
    "xyz_id": "5f3c8e9a1b2c3d4e5f6a7b8c",
    "name": "示例播客",
    "category": "科技",
    "description": "这是一个示例播客"
  }'
```

### 3. 查询播客列表

```bash
curl "http://localhost:8000/api/podcasts/?skip=0&limit=10&category=科技"
```

### 4. 执行数据抓取

```bash
curl -X POST "http://localhost:8000/api/scraper/run"
```

## 🗂️ 项目结构

```
xyzrank_v6/
├── backend/
│   ├── app/
│   │   ├── api/              # API 路由
│   │   │   ├── podcasts.py   # 播客管理 API
│   │   │   ├── imports.py    # 数据导入 API
│   │   │   └── scraper.py    # 爬虫 API
│   │   ├── core/             # 核心配置
│   │   │   └── config.py     # 应用配置
│   │   ├── db/               # 数据库
│   │   │   └── session.py    # 数据库会话
│   │   ├── models/           # 数据模型
│   │   │   └── podcast.py    # 播客相关模型
│   │   ├── services/         # 业务逻辑服务
│   │   │   ├── import_service.py   # 数据导入服务
│   │   │   └── scraper_service.py  # 爬虫服务
│   │   ├── tasks/            # 定时任务
│   │   │   └── scheduler.py  # 任务调度器
│   │   └── main.py           # 应用入口
│   ├── migrations/           # 数据库迁移
│   └── requirements.txt      # 依赖列表
├── SPEC.md                   # 需求文档
└── README.md                 # 本文件
```

## 🔧 配置说明

### 数据库配置

在 `.env` 文件中配置 MySQL 连接信息：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=xyzrank
MYSQL_PASSWORD=your_password
MYSQL_DB=xyzrank
```

### 定时任务配置

定时任务默认每天凌晨 2:00 执行。可以在 `app/tasks/scheduler.py` 中修改执行时间。

## 📝 数据模型

### Podcast（播客）
- `id`: 主键
- `xyz_id`: 小宇宙ID（唯一）
- `name`: 播客名称
- `rss_url`: RSS 链接
- `cover_url`: 封面图URL
- `category`: 分类
- `description`: 描述
- `created_at`: 创建时间
- `updated_at`: 更新时间

### PodcastDailyMetric（每日指标）
- `id`: 主键
- `podcast_id`: 播客ID（外键）
- `snapshot_date`: 快照日期
- `subscriber_count`: 订阅者数量
- `created_at`: 创建时间

### ScrapeRun（抓取任务记录）
- `id`: 主键
- `started_at`: 开始时间
- `completed_at`: 完成时间
- `status`: 状态（running/completed/failed）
- `total_podcasts`: 总播客数
- `successful_count`: 成功数量
- `failed_count`: 失败数量
- `error_message`: 错误信息

## 🔄 数据库迁移

```bash
# 创建新的迁移
alembic revision --autogenerate -m "描述信息"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## ⚠️ 注意事项

1. **爬虫实现**：当前爬虫服务提供了基础框架，需要根据小宇宙平台的实际 API 或页面结构进行完善。

2. **数据准确性**：订阅者数量抓取可能需要登录或 API Key，需要根据实际情况实现。

3. **请求频率**：注意遵守网站的 robots.txt 和使用条款，避免请求过于频繁导致被封禁。

4. **环境变量**：生产环境请使用安全的密码和配置，不要将敏感信息提交到代码仓库。

## 🛠️ 开发计划

- [x] 基础架构搭建
- [x] 数据模型设计
- [x] CRUD API 实现
- [x] 数据导入功能
- [x] 爬虫服务框架
- [x] 定时任务框架
- [ ] 完善爬虫实现
- [ ] 添加错误处理和重试机制
- [ ] 性能优化
- [ ] 单元测试
- [ ] 数据分析和统计 API
- [ ] 排名计算功能

## 📄 许可证

本项目仅供学习和研究使用。

## 📞 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

---

详细的需求文档请参考 [SPEC.md](./SPEC.md)

