# 爬虫体系开发指南

> 本文档专门记录爬虫体系的开发计划、技术方案和实现细节。

---

## 📋 当前状态

### ✅ 已完成

1. **基础架构**
   - `PodcastScraper` 类框架
   - 爬虫API接口
   - 定时任务调度器
   - 数据模型（ScrapeRun）

2. **基础功能**
   - `scrape_podcast_info()` - 抓取播客基本信息（基础版本）
   - `update_podcast_from_scrape()` - 更新播客信息
   - `record_daily_metric()` - 记录每日指标
   - `scrape_all_podcasts()` - 批量抓取框架

3. **测试工具**
   - `test_scraper_batch.py` - 批量测试脚本

### ⚠️ 待实现

1. **核心功能**
   - `scrape_subscriber_count()` - 抓取订阅者数量（**关键功能，待实现**）
   - 页面解析逻辑优化（需要根据实际页面结构调整）

2. **高级功能**
   - 反爬虫策略
   - 错误处理和重试机制
   - 并发控制优化
   - 增量更新

---

## 🎯 开发目标

### 阶段一：核心功能实现

**目标**: 实现订阅数抓取功能，使爬虫系统能够正常工作。

**任务清单**:
1. [ ] 分析小宇宙平台的订阅数获取方式
   - 检查是否有公开API
   - 分析页面结构（静态/动态）
   - 确定数据获取方法

2. [ ] 实现 `scrape_subscriber_count()` 方法
   - 方案A: 如果存在API，实现API调用
   - 方案B: 如果页面静态，使用BeautifulSoup解析
   - 方案C: 如果页面动态，使用Playwright/Selenium

3. [ ] 优化 `scrape_podcast_info()` 方法
   - 根据实际页面结构调整解析规则
   - 增加容错机制
   - 处理页面结构变化

4. [ ] 测试和验证
   - 测试单个播客抓取
   - 测试批量抓取（小规模）
   - 验证数据准确性

### 阶段二：体系完善

**目标**: 完善爬虫体系，提高稳定性和效率。

**任务清单**:
1. [ ] 反爬虫策略
   - 请求频率控制
   - User-Agent 轮换
   - 请求头设置
   - Cookie/Session 管理（如需要）
   - IP代理池（如需要）

2. [ ] 并发控制优化
   - 可配置并发数
   - 动态调整并发策略
   - 请求队列管理

3. [ ] 错误处理和重试
   - 网络错误重试（指数退避）
   - 解析错误处理
   - 失败记录和报告
   - 异常数据标记

4. [ ] 增量更新
   - 只抓取需要更新的播客
   - 智能判断更新频率
   - 避免重复抓取

### 阶段三：监控和优化

**目标**: 添加监控功能，优化性能。

**任务清单**:
1. [ ] 爬取监控
   - 实时查看爬取进度
   - 成功/失败统计
   - 性能指标（耗时、速度等）

2. [ ] 日志系统
   - 详细的爬取日志
   - 错误日志分类
   - 日志查询和分析

3. [ ] 告警机制
   - 爬取失败告警
   - 数据异常告警
   - 系统异常告警

---

## 🔍 技术方案分析

### 1. 订阅数获取方式

#### 方案A: API调用

**优点**:
- 速度快
- 数据格式规范
- 稳定性高

**缺点**:
- 可能需要认证
- API可能不稳定或变更

**实现步骤**:
1. 分析小宇宙平台的网络请求
2. 找到订阅数相关的API端点
3. 实现API调用逻辑
4. 处理认证（如需要）

#### 方案B: 静态页面解析

**优点**:
- 不需要认证
- 实现简单

**缺点**:
- 页面结构可能变化
- 需要处理各种页面格式

**实现步骤**:
1. 分析页面HTML结构
2. 使用BeautifulSoup解析
3. 提取订阅数数据
4. 处理各种页面格式

#### 方案C: 动态页面渲染

**优点**:
- 可以处理JavaScript渲染的内容
- 更接近真实浏览器行为

**缺点**:
- 性能较低
- 资源消耗大

**实现步骤**:
1. 使用Playwright或Selenium
2. 等待页面加载完成
3. 提取订阅数数据
4. 优化性能（无头模式、资源过滤等）

### 2. 反爬虫策略

#### 请求频率控制

```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window  # 秒
        self.requests = []
    
    async def acquire(self):
        now = datetime.now()
        # 清理过期请求
        self.requests = [r for r in self.requests if now - r < timedelta(seconds=self.time_window)]
        
        if len(self.requests) >= self.max_requests:
            # 等待
            sleep_time = self.time_window - (now - self.requests[0]).total_seconds()
            await asyncio.sleep(sleep_time)
        
        self.requests.append(now)
```

#### User-Agent 轮换

```python
import random

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    # ... 更多User-Agent
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)
```

#### 请求头设置

```python
headers = {
    "User-Agent": get_random_user_agent(),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}
```

### 3. 错误处理和重试

```python
import asyncio
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff ** attempt)
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            raise last_exception
        return wrapper
    return decorator

# 使用示例
@retry(max_attempts=3, delay=1.0, backoff=2.0)
async def scrape_with_retry(xyz_id: str):
    # 爬取逻辑
    pass
```

### 4. 并发控制

```python
import asyncio

class ConcurrencyController:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute(self, coro):
        async with self.semaphore:
            return await coro

# 使用示例
controller = ConcurrencyController(max_concurrent=5)
tasks = [controller.execute(scrape_podcast(p)) for p in podcasts]
results = await asyncio.gather(*tasks)
```

---

## 📝 代码实现建议

### 1. 改进 `scrape_podcast_info()` 方法

```python
async def scrape_podcast_info(self, xyz_id: str) -> Optional[dict]:
    """
    抓取播客基本信息（改进版）
    """
    try:
        url = f"https://www.xiaoyuzhou.fm/podcast/{xyz_id}"
        
        # 设置请求头
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        info = {}
        
        # 多种方式尝试获取名称
        title_tag = soup.find("title")
        if title_tag:
            info["name"] = title_tag.get_text().strip()
        
        # 尝试从 meta 标签获取
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title and not info.get("name"):
            info["name"] = og_title.get("content", "").strip()
        
        # 类似地处理其他字段...
        
        return info
        
    except Exception as e:
        logger.error(f"抓取播客 {xyz_id} 信息失败: {e}")
        return None
```

### 2. 实现 `scrape_subscriber_count()` 方法

```python
async def scrape_subscriber_count(self, xyz_id: str) -> Optional[int]:
    """
    抓取播客订阅者数量
    
    需要根据实际平台实现：
    1. 如果存在API，调用API
    2. 如果页面静态，解析HTML
    3. 如果页面动态，使用Playwright
    """
    try:
        # 方案1: API调用（如果存在）
        # api_url = f"https://api.xiaoyuzhou.fm/podcast/{xyz_id}/stats"
        # response = await self.client.get(api_url)
        # data = response.json()
        # return data.get("subscriber_count")
        
        # 方案2: 静态页面解析
        url = f"https://www.xiaoyuzhou.fm/podcast/{xyz_id}"
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 根据实际页面结构解析订阅数
        # 示例：查找包含"订阅"文本的元素
        subscriber_elements = soup.find_all(string=lambda text: text and "订阅" in text)
        # 进一步解析...
        
        # 方案3: 动态页面渲染（如果需要）
        # from playwright.async_api import async_playwright
        # async with async_playwright() as p:
        #     browser = await p.chromium.launch(headless=True)
        #     page = await browser.new_page()
        #     await page.goto(url)
        #     # 等待内容加载
        #     await page.wait_for_selector("...")
        #     # 提取订阅数
        #     count = await page.text_content("...")
        #     await browser.close()
        
        return None  # 待实现
        
    except Exception as e:
        logger.error(f"抓取播客 {xyz_id} 订阅者数量失败: {e}")
        return None
```

### 3. 改进 `scrape_all_podcasts()` 方法

```python
async def scrape_all_podcasts(self) -> ScrapeRun:
    """
    抓取所有播客的数据（改进版）
    """
    scrape_run = ScrapeRun(status="running", started_at=datetime.now())
    self.session.add(scrape_run)
    await self.session.commit()
    await self.session.refresh(scrape_run)
    
    try:
        result = await self.session.execute(select(Podcast))
        podcasts = result.scalars().all()
        
        scrape_run.total_podcasts = len(podcasts)
        successful_count = 0
        failed_count = 0
        today = date.today()
        
        # 并发控制
        semaphore = asyncio.Semaphore(5)  # 最多5个并发
        
        async def process_podcast(podcast: Podcast):
            async with semaphore:
                try:
                    # 更新播客信息
                    await self.update_podcast_from_scrape(podcast)
                    
                    # 抓取订阅者数量
                    subscriber_count = await self.scrape_subscriber_count(podcast.xyz_id)
                    if subscriber_count is not None:
                        await self.record_daily_metric(
                            podcast.id, today, subscriber_count
                        )
                        return True
                    return False
                except Exception as e:
                    logger.error(f"处理播客 {podcast.xyz_id} 时出错: {e}")
                    return False
        
        # 批量处理
        tasks = [process_podcast(p) for p in podcasts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        for result in results:
            if result is True:
                successful_count += 1
            else:
                failed_count += 1
        
        scrape_run.status = "completed"
        scrape_run.completed_at = datetime.now()
        scrape_run.successful_count = successful_count
        scrape_run.failed_count = failed_count
        
    except Exception as e:
        scrape_run.status = "failed"
        scrape_run.completed_at = datetime.now()
        scrape_run.error_message = str(e)
        logger.error(f"批量抓取失败: {e}")
    
    await self.session.commit()
    await self.session.refresh(scrape_run)
    return scrape_run
```

---

## 🧪 测试计划

### 1. 单元测试

- [ ] 测试 `scrape_podcast_info()` 方法
- [ ] 测试 `scrape_subscriber_count()` 方法
- [ ] 测试 `record_daily_metric()` 方法
- [ ] 测试错误处理逻辑

### 2. 集成测试

- [ ] 测试单个播客抓取流程
- [ ] 测试批量抓取流程
- [ ] 测试定时任务触发
- [ ] 测试API接口

### 3. 性能测试

- [ ] 测试并发性能
- [ ] 测试大量数据抓取
- [ ] 测试资源消耗

### 4. 稳定性测试

- [ ] 长时间运行测试
- [ ] 错误恢复测试
- [ ] 网络异常测试

---

## 📚 参考资料

1. **HTTPX文档**: https://www.python-httpx.org/
2. **BeautifulSoup文档**: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
3. **Playwright文档**: https://playwright.dev/python/
4. **APScheduler文档**: https://apscheduler.readthedocs.io/

---

## 🔗 相关文件

- `backend/app/services/scraper_service.py` - 爬虫服务实现
- `backend/app/api/scraper.py` - 爬虫API接口
- `backend/app/tasks/scheduler.py` - 定时任务调度器
- `backend/test_scraper_batch.py` - 批量测试脚本
- `backend/app/models/podcast.py` - 数据模型（含ScrapeRun）

---

**文档维护**: 请在每次实现新功能后更新本文档。


