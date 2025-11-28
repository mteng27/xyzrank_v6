# 反爬虫策略指南

> 本文档说明如何配置和使用反爬虫策略，避免被目标网站封禁。

---

## 📋 策略概览

我们实现了以下反爬虫策略：

### 1. 请求频率控制 (Rate Limiting)
- **令牌桶算法**：控制时间窗口内的请求数量
- **默认配置**：每分钟最多 10 个请求
- **可配置**：`max_requests` 和 `time_window`

### 2. User-Agent 轮换
- **多浏览器支持**：Chrome、Safari、Firefox、Edge
- **多平台支持**：Windows、macOS
- **策略**：随机选择或顺序轮换

### 3. 请求间隔随机化
- **正态分布延迟**：模拟人类行为
- **默认配置**：3-6 秒随机延迟
- **可配置**：`min_delay`、`max_delay`、`base_delay`

### 4. 请求头随机化
- **真实浏览器请求头**：包含所有必要的 HTTP 头
- **平台相关**：根据 User-Agent 自动调整
- **安全相关**：包含 `Sec-Fetch-*` 等现代浏览器头

### 5. 重试机制（指数退避）
- **自动重试**：网络错误时自动重试
- **指数退避**：延迟时间逐渐增加
- **随机抖动**：避免雷群效应
- **默认配置**：最多重试 3 次

---

## 🚀 使用方法

### 基本使用

```python
from app.services.scraper_service import PodcastScraper
from app.db.session import get_db_session

# 使用默认反爬虫策略
async with get_db_session() as session:
    scraper = PodcastScraper(session)
    # 自动应用反爬虫策略
    subscriber_count = await scraper.scrape_subscriber_count(xyz_id)
```

### 自定义配置

```python
from app.services.scraper_service import PodcastScraper
from app.services.anti_scraping import create_anti_scraping_manager

# 自定义反爬虫配置
custom_config = {
    "rate_limiter": {
        "max_requests": 5,   # 每分钟最多5个请求（更保守）
        "time_window": 60
    },
    "request_delay": {
        "min_delay": 5.0,    # 最小延迟5秒
        "max_delay": 10.0,   # 最大延迟10秒
        "base_delay": 7.0    # 基础延迟7秒
    },
    "retry_strategy": {
        "max_attempts": 5,   # 最多重试5次
        "initial_delay": 3.0,
        "max_delay": 60.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}

# 创建自定义反爬虫管理器
anti_scraping = create_anti_scraping_manager(custom_config)

# 使用自定义配置
async with get_db_session() as session:
    scraper = PodcastScraper(session, anti_scraping_manager=anti_scraping)
    subscriber_count = await scraper.scrape_subscriber_count(xyz_id)
```

---

## ⚙️ 配置说明

### 保守策略（推荐用于生产环境）

```python
CONSERVATIVE_CONFIG = {
    "rate_limiter": {
        "max_requests": 5,   # 每分钟5个请求
        "time_window": 60
    },
    "request_delay": {
        "min_delay": 5.0,    # 5-10秒延迟
        "max_delay": 10.0,
        "base_delay": 7.0
    },
    "retry_strategy": {
        "max_attempts": 3,
        "initial_delay": 3.0,
        "max_delay": 60.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}
```

### 平衡策略（默认）

```python
BALANCED_CONFIG = {
    "rate_limiter": {
        "max_requests": 10,  # 每分钟10个请求
        "time_window": 60
    },
    "request_delay": {
        "min_delay": 3.0,    # 3-6秒延迟
        "max_delay": 6.0,
        "base_delay": 4.0
    },
    "retry_strategy": {
        "max_attempts": 3,
        "initial_delay": 2.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}
```

### 快速策略（仅用于测试，不推荐生产环境）

```python
FAST_CONFIG = {
    "rate_limiter": {
        "max_requests": 20,  # 每分钟20个请求
        "time_window": 60
    },
    "request_delay": {
        "min_delay": 1.0,    # 1-3秒延迟
        "max_delay": 3.0,
        "base_delay": 2.0
    },
    "retry_strategy": {
        "max_attempts": 2,
        "initial_delay": 1.0,
        "max_delay": 10.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}
```

---

## 📊 监控和统计

### 获取统计信息

```python
# 获取反爬虫管理器统计信息
stats = scraper.anti_scraping.get_stats()
print(stats)
# {
#     "rate_limiter": {
#         "current_requests": 5,
#         "max_requests": 10,
#         "time_window": 60,
#         "wait_time": 0.0
#     },
#     "user_agent": {
#         "current_index": 3,
#         "total_agents": 10
#     }
# }
```

---

## 🛡️ 最佳实践

### 1. 生产环境配置

- ✅ 使用**保守策略**（每分钟5个请求）
- ✅ 设置较长的延迟（5-10秒）
- ✅ 启用重试机制（最多3-5次）
- ✅ 监控请求频率和错误率

### 2. 批量抓取

```python
# 批量抓取时，建议：
# 1. 使用较低的并发数（最多3-5个并发）
# 2. 每个请求之间添加延迟
# 3. 分批处理，避免一次性抓取太多

async def scrape_batch(podcasts, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def scrape_one(podcast):
        async with semaphore:
            # 反爬虫策略会自动应用
            return await scraper.scrape_subscriber_count(podcast.xyz_id)
    
    tasks = [scrape_one(p) for p in podcasts]
    return await asyncio.gather(*tasks)
```

### 3. 错误处理

```python
# 如果遇到 429 (Too Many Requests) 或 403 (Forbidden)：
# 1. 立即停止请求
# 2. 增加延迟时间
# 3. 减少并发数
# 4. 等待一段时间后再继续

if response.status_code == 429:
    logger.warning("遇到频率限制，等待更长时间...")
    await asyncio.sleep(300)  # 等待5分钟
    # 调整配置，降低请求频率
```

### 4. 日志记录

```python
# 记录所有请求，便于分析
logger.info(f"请求 {url}, User-Agent: {headers['User-Agent']}")
logger.info(f"延迟: {delay:.2f}秒")
logger.info(f"频率限制: {stats['rate_limiter']['current_requests']}/{stats['rate_limiter']['max_requests']}")
```

---

## ⚠️ 注意事项

1. **不要过于激进**
   - 即使有反爬虫策略，也不要设置过高的请求频率
   - 建议每分钟不超过 10 个请求

2. **监控错误率**
   - 如果错误率突然增加，可能是被封禁的前兆
   - 立即降低请求频率

3. **遵守 robots.txt**
   - 检查目标网站的 robots.txt
   - 遵守爬取规则

4. **使用代理（可选）**
   - 如果需要更高的请求频率，考虑使用代理池
   - 当前实现不包含代理，需要时可以扩展

5. **定期更新 User-Agent**
   - 定期更新 User-Agent 列表，使用最新版本
   - 避免使用过时的浏览器版本

---

## 🔧 扩展功能

### 添加代理支持

```python
# 可以在 AntiScrapingManager 中添加代理轮换
class ProxyRotator:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.current_index = 0
    
    def get_next(self) -> str:
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
```

### 添加 Cookie 管理

```python
# 如果需要登录或保持会话
class CookieManager:
    def __init__(self):
        self.cookies = {}
    
    def update(self, cookies: Dict):
        self.cookies.update(cookies)
    
    def get(self) -> Dict:
        return self.cookies
```

---

## 📈 性能优化

1. **并发控制**：使用信号量限制并发数
2. **批量处理**：分批处理，避免一次性处理太多
3. **缓存**：缓存已抓取的数据，避免重复请求
4. **增量更新**：只抓取需要更新的播客

---

## 📝 配置示例

### 环境变量配置

```bash
# .env 文件
SCRAPER_MAX_REQUESTS_PER_MINUTE=10
SCRAPER_MIN_DELAY=3.0
SCRAPER_MAX_DELAY=6.0
SCRAPER_MAX_RETRIES=3
```

### 代码中使用

```python
import os
from app.services.anti_scraping import create_anti_scraping_manager

config = {
    "rate_limiter": {
        "max_requests": int(os.getenv("SCRAPER_MAX_REQUESTS_PER_MINUTE", 10)),
        "time_window": 60
    },
    "request_delay": {
        "min_delay": float(os.getenv("SCRAPER_MIN_DELAY", 3.0)),
        "max_delay": float(os.getenv("SCRAPER_MAX_DELAY", 6.0)),
        "base_delay": 4.0
    },
    "retry_strategy": {
        "max_attempts": int(os.getenv("SCRAPER_MAX_RETRIES", 3)),
        "initial_delay": 2.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}

anti_scraping = create_anti_scraping_manager(config)
```

---

**最后更新**: 2025-01-XX


