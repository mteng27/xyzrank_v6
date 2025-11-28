# XYZRank 项目状态文档

> 最后更新: 2025-01-XX
> 
> 本文档记录 XYZRank 播客排名系统的当前状态、已完成功能、现有代码结构，以及后续开发计划。

---

## 📋 项目概述

**XYZRank** 是一个小宇宙播客数据追踪与分析平台，主要功能包括：
- 播客基础信息管理
- 每日订阅数追踪
- 增长趋势可视化
- 自动数据爬取
- 数据导入导出

---

## ✅ 已完成功能

### 1. 后端系统

#### 1.1 数据模型 (`backend/app/models/podcast.py`)

**Podcast (播客表)**
- `id`: 主键
- `xyz_id`: 小宇宙播客ID（唯一）
- `name`: 播客名称
- `rss_url`: RSS链接
- `cover_url`: 封面图URL
- `category`: 分类
- `description`: 描述
- `created_at`, `updated_at`: 时间戳
- 关联关系: `daily_metrics` (一对多)

**PodcastDailyMetric (每日指标表)**
- `id`: 主键
- `podcast_id`: 播客ID（外键）
- `snapshot_date`: 快照日期
- `subscriber_count`: 订阅者数量
- `created_at`: 创建时间
- 唯一约束: `(podcast_id, snapshot_date)`

**ScrapeRun (爬取运行记录表)**
- `id`: 主键
- `started_at`: 开始时间
- `completed_at`: 完成时间
- `status`: 状态 (running, completed, failed)
- `total_podcasts`: 总播客数
- `successful_count`: 成功数
- `failed_count`: 失败数
- `error_message`: 错误信息

#### 1.2 API 接口

**播客管理 API** (`/api/podcasts`)
- `GET /api/podcasts/` - 获取播客列表（支持分页、分类筛选、搜索、排序）
- `GET /api/podcasts/{podcast_id}` - 获取单个播客详情
- `POST /api/podcasts/` - 创建新播客
- `PUT /api/podcasts/{podcast_id}` - 更新播客信息
- `DELETE /api/podcasts/{podcast_id}` - 删除播客
- `GET /api/podcasts/{podcast_id}/metrics` - 获取播客历史指标
- `POST /api/podcasts/{podcast_id}/metrics` - 添加每日指标
- `PUT /api/podcasts/metrics/{metric_id}` - 更新指标
- `DELETE /api/podcasts/metrics/{metric_id}` - 删除指标

**数据导入 API** (`/api/imports`)
- `POST /api/imports/excel` - 从Excel文件导入播客数据

**爬虫 API** (`/api/scraper`)
- `POST /api/scraper/run` - 执行一次完整的播客数据抓取
- `POST /api/scraper/podcast/{podcast_id}` - 抓取单个播客的数据
- `GET /api/scraper/runs` - 获取爬取运行历史

#### 1.3 服务层

**ImportService** (`backend/app/services/import_service.py`)
- 从Excel文件导入播客基础信息
- 支持批量导入和历史订阅数据导入
- 自动处理重复数据

**ScraperService** (`backend/app/services/scraper_service.py`)
- `PodcastScraper` 类：播客数据爬虫
- `scrape_podcast_info()`: 抓取播客基本信息
- `scrape_subscriber_count()`: 抓取订阅者数量（待实现）
- `update_podcast_from_scrape()`: 更新播客信息
- `record_daily_metric()`: 记录每日指标
- `scrape_all_podcasts()`: 批量抓取所有播客

#### 1.4 定时任务

**Scheduler** (`backend/app/tasks/scheduler.py`)
- 使用 APScheduler 实现定时任务
- 每日凌晨 2:00 自动执行数据抓取
- 支持任务启动和关闭管理

#### 1.5 数据库配置

- **当前使用**: SQLite (本地开发)
- **配置位置**: `backend/app/core/config.py`
- **会话管理**: `backend/app/db/session.py` (异步SQLAlchemy)

### 2. 前端系统

#### 2.1 主要功能 (`frontend/index.html`)

**数据展示**
- 播客列表展示（支持分页）
- 按订阅数或创建时间排序
- 分类筛选
- 实时搜索（支持中文搜索）
- 统计信息展示（总播客数、当前显示数、分类筛选）

**趋势可视化**
- 每个播客项右侧显示增长趋势图
- 使用 Chart.js 绘制折线图
- 显示统计数据：
  - 总增长数
  - 增长率
  - 最近增长
- 根据增长趋势自动显示颜色（绿色=增长，红色=下降）

**布局设计**
- 响应式设计
- 每个播客项一行显示
- 左侧：节目信息（排名、名称、订阅数、分类、描述）
- 右侧：增长趋势图表和统计数据

#### 2.2 技术栈
- HTML5 + CSS3
- 原生 JavaScript (ES6+)
- Chart.js (图表库)
- Fetch API (HTTP请求)

### 3. 数据导入

**已完成的数据导入**
- ✅ 从 `小宇宙全量专辑.csv` 导入播客基础信息（7,202条）
- ✅ 从 `小宇宙播客部分订阅量.csv` 导入历史订阅数据
- ✅ 自动处理缺失的播客记录
- ✅ 数据验证和去重

**导入脚本**
- `backend/setup_and_import.py`: 完整的数据导入流程
- `backend/setup_with_sqlite.py`: SQLite版本的数据导入

---

## 🔧 现有爬虫体系架构

### 1. 代码结构

```
backend/
├── app/
│   ├── api/
│   │   └── scraper.py              # 爬虫API路由
│   ├── services/
│   │   └── scraper_service.py       # 爬虫服务核心逻辑
│   ├── tasks/
│   │   └── scheduler.py            # 定时任务调度器
│   └── models/
│       └── podcast.py              # 数据模型（含ScrapeRun）
├── test_scraper_batch.py           # 批量测试脚本
└── requirements.txt                # 依赖包列表
```

### 2. 爬虫服务类 (`PodcastScraper`)

**核心方法**

1. **`scrape_podcast_info(xyz_id: str)`**
   - 功能: 抓取播客基本信息
   - URL: `https://www.xiaoyuzhou.fm/podcast/{xyz_id}`
   - 解析内容:
     - 名称 (从 `<title>` 标签)
     - RSS链接 (从 `<link type="application/rss+xml">`)
     - 封面图 (从 `<meta property="og:image">`)
     - 描述 (从 `<meta name="description">`)
   - 状态: ✅ 已实现（基础版本，需要根据实际页面结构调整）

2. **`scrape_subscriber_count(xyz_id: str)`**
   - 功能: 抓取订阅者数量
   - 状态: ⚠️ **待实现**（需要根据实际API或页面结构实现）
   - 备注: 可能需要登录、API key、或更复杂的爬虫技术

3. **`update_podcast_from_scrape(podcast: Podcast)`**
   - 功能: 从爬取的数据更新播客信息
   - 状态: ✅ 已实现

4. **`record_daily_metric(podcast_id, snapshot_date, subscriber_count)`**
   - 功能: 记录每日指标
   - 状态: ✅ 已实现
   - 特性: 自动处理重复日期（更新而非插入）

5. **`scrape_all_podcasts()`**
   - 功能: 批量抓取所有播客的数据
   - 状态: ✅ 已实现（框架完成，但依赖 `scrape_subscriber_count` 的实现）
   - 流程:
     1. 创建 `ScrapeRun` 记录
     2. 遍历所有播客
     3. 更新播客信息
     4. 抓取订阅数并记录
     5. 更新 `ScrapeRun` 状态

### 3. API 接口

**`POST /api/scraper/run`**
- 功能: 手动触发一次完整的抓取任务
- 返回: `ScrapeRunResponse` (包含运行状态、成功数、失败数等)

**`POST /api/scraper/podcast/{podcast_id}`**
- 功能: 抓取单个播客的数据
- 返回: 更新状态和播客信息

**`GET /api/scraper/runs`**
- 功能: 获取爬取运行历史
- 参数: `limit` (默认20)
- 返回: `ScrapeRunResponse` 列表

### 4. 定时任务

**配置** (`scheduler.py`)
- 调度器: `AsyncIOScheduler` (APScheduler)
- 触发时间: 每天凌晨 2:00
- 任务函数: `daily_scrape_task()`
- 生命周期: 在 FastAPI `lifespan` 中启动和关闭

### 5. 测试工具

**`test_scraper_batch.py`**
- 功能: 批量测试播客数据抓取（检测100个网址的数据可用性）
- 特性:
  - 并发控制（最多5个并发请求）
  - 数据可用性检测（标题、RSS、封面、描述）
  - 生成测试报告
  - 保存详细结果到JSON文件

---

## 📊 数据统计

### 当前数据库状态
- **播客总数**: 7,202+
- **有订阅数据的播客**: 部分（来自历史导入）
- **每日指标记录**: 多个时间点的快照数据

### 数据来源
1. **基础信息**: `小宇宙全量专辑.csv`
2. **历史订阅数据**: `小宇宙播客部分订阅量.csv`

---

## 🚧 待开发功能

### 1. 爬虫体系完善

#### 1.1 核心功能
- [ ] **实现 `scrape_subscriber_count()` 方法**
  - 需要分析小宇宙平台的订阅数获取方式
  - 可能需要：
    - API调用（需要认证）
    - 页面解析（需要处理JavaScript渲染）
    - 使用 Playwright/Selenium 处理动态内容

- [ ] **优化页面解析逻辑**
  - 根据实际页面结构调整 `scrape_podcast_info()` 的解析规则
  - 处理页面结构变化（容错机制）

- [ ] **实现反爬虫策略**
  - 请求频率控制
  - User-Agent 轮换
  - IP代理池（如需要）
  - Cookie/Session 管理（如需要）

#### 1.2 高级功能
- [ ] **并发控制优化**
  - 当前使用信号量控制（5个并发）
  - 可配置并发数
  - 动态调整并发策略

- [ ] **错误处理和重试机制**
  - 网络错误重试
  - 解析错误处理
  - 失败记录和报告

- [ ] **数据验证**
  - 抓取数据的有效性检查
  - 异常数据标记
  - 数据质量报告

- [ ] **增量更新**
  - 只抓取需要更新的播客
  - 智能判断更新频率
  - 避免重复抓取

#### 1.3 监控和日志
- [ ] **爬取监控**
  - 实时查看爬取进度
  - 成功/失败统计
  - 性能指标（耗时、速度等）

- [ ] **日志系统**
  - 详细的爬取日志
  - 错误日志分类
  - 日志查询和分析

- [ ] **告警机制**
  - 爬取失败告警
  - 数据异常告警
  - 系统异常告警

### 2. 前端功能增强

- [ ] **爬取状态展示**
  - 显示最近一次爬取状态
  - 爬取历史记录
  - 手动触发爬取按钮

- [ ] **数据导出**
  - 导出播客列表（CSV/Excel）
  - 导出趋势数据
  - 导出报告

- [ ] **高级筛选**
  - 多条件组合筛选
  - 时间范围筛选
  - 增长趋势筛选

### 3. 系统优化

- [ ] **性能优化**
  - 数据库查询优化
  - 前端加载优化
  - API响应缓存

- [ ] **安全性**
  - API认证和授权
  - 数据访问控制
  - 防止SQL注入等安全问题

---

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI 0.115.0
- **ORM**: SQLAlchemy 2.0.36 (异步)
- **数据库**: SQLite (开发) / MySQL (生产)
- **HTTP客户端**: httpx 0.27.2
- **HTML解析**: BeautifulSoup4 4.12.3
- **任务调度**: APScheduler 3.10.4
- **浏览器自动化**: Playwright 1.47.0 (已安装，待使用)
- **数据处理**: Pandas 2.2.3
- **日志**: Loguru 0.7.2

### 前端
- **HTML5 + CSS3**
- **JavaScript (ES6+)**
- **Chart.js** (图表库)

### 开发工具
- **数据库迁移**: Alembic 1.13.3
- **环境配置**: python-dotenv 1.0.1
- **数据验证**: Pydantic + pydantic-settings

---

## 📝 开发计划

### 阶段一：爬虫核心功能实现
1. 分析小宇宙平台的订阅数获取方式
2. 实现 `scrape_subscriber_count()` 方法
3. 优化页面解析逻辑
4. 测试和验证爬取功能

### 阶段二：爬虫体系完善
1. 实现反爬虫策略
2. 优化并发控制
3. 添加错误处理和重试机制
4. 实现增量更新

### 阶段三：监控和优化
1. 添加爬取监控功能
2. 完善日志系统
3. 性能优化
4. 前端功能增强

---

## 📚 相关文档

- `backend/FINAL_IMPORT_REPORT.md` - 数据导入报告
- `backend/IMPORT_GUIDE.md` - 数据导入指南
- `backend/README.md` - 后端README（如果存在）

---

## 🔗 重要文件路径

```
项目根目录/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── podcasts.py          # 播客API
│   │   │   ├── imports.py           # 导入API
│   │   │   └── scraper.py           # 爬虫API
│   │   ├── services/
│   │   │   ├── import_service.py    # 导入服务
│   │   │   └── scraper_service.py   # 爬虫服务
│   │   ├── tasks/
│   │   │   └── scheduler.py         # 定时任务
│   │   ├── models/
│   │   │   └── podcast.py           # 数据模型
│   │   └── main.py                  # 应用入口
│   ├── test_scraper_batch.py        # 批量测试脚本
│   └── requirements.txt             # 依赖包
├── frontend/
│   └── index.html                   # 前端页面
└── PROJECT_STATUS.md                # 本文档
```

---

## 📌 注意事项

1. **爬虫实现**
   - 当前 `scrape_subscriber_count()` 方法尚未实现，需要根据实际平台API或页面结构完成
   - 页面解析逻辑可能需要根据实际HTML结构调整

2. **数据库**
   - 当前使用SQLite用于本地开发
   - 生产环境建议使用MySQL或PostgreSQL

3. **定时任务**
   - 定时任务在应用启动时自动启动
   - 可通过API手动触发爬取任务

4. **数据导入**
   - 已完成历史数据导入
   - 后续数据更新主要通过爬虫系统完成

---

**文档维护**: 请在每次重大更新后更新本文档。


