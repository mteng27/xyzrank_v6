# 爬虫调度策略说明

## 📅 调度方案

### 目标
- **一周内完成所有7000个播客的爬取**
- **每天爬取约1000个播客**（7000 ÷ 7 ≈ 1000）

### 实现策略

#### 1. 基于哈希值的轮询机制
使用播客ID的哈希值对周期天数取模，确保：
- 每个播客在7天内会被爬取一次
- 每天爬取不同的播客集合
- 分布均匀，避免集中在某些播客

**算法**：
```python
day_of_cycle = today.toordinal() % 7  # 0-6
podcasts_to_scrape = [
    p for p in all_podcasts
    if hash(p.id) % 7 == day_of_cycle
]
```

#### 2. 执行时间
- **默认时间**：每天凌晨 2:00
- **可配置**：在 `scheduler.py` 中修改 `CronTrigger`

#### 3. 并发控制
- **并发数**：3个（通过 `AntiScrapingManager` 控制）
- **请求频率**：每分钟10个请求
- **延迟**：3-6秒随机延迟

## 🔧 配置选项

### 修改每天爬取数量
在 `scheduler.py` 的 `daily_scrape_task()` 中修改：
```python
scrape_run = await scraper.scrape_podcasts_batch(
    batch_size=1000,  # 修改这个值
    days_in_cycle=7
)
```

### 修改周期天数
```python
scrape_run = await scraper.scrape_podcasts_batch(
    batch_size=1000,
    days_in_cycle=7  # 修改这个值（例如改为14天）
)
```

### 修改执行时间
在 `scheduler.py` 的 `setup_scheduler()` 中修改：
```python
scheduler.add_job(
    daily_scrape_task,
    trigger=CronTrigger(hour=2, minute=0),  # 修改这里
    ...
)
```

## 📊 预期效果

### 第一周
- **第1天**：爬取约1000个播客（ID哈希值 % 7 == 0）
- **第2天**：爬取约1000个播客（ID哈希值 % 7 == 1）
- **第3天**：爬取约1000个播客（ID哈希值 % 7 == 2）
- **第4天**：爬取约1000个播客（ID哈希值 % 7 == 3）
- **第5天**：爬取约1000个播客（ID哈希值 % 7 == 4）
- **第6天**：爬取约1000个播客（ID哈希值 % 7 == 5）
- **第7天**：爬取约1000个播客（ID哈希值 % 7 == 6）

### 第二周及以后
- 重复第一周的循环
- 每个播客每周更新一次数据

## ⚙️ 高级选项

### 方案A：每天固定数量（当前实现）
- 优点：简单，可预测
- 缺点：如果播客总数变化，分布可能不均匀

### 方案B：基于上次爬取时间
优先爬取长时间未更新的播客：
```python
# 获取7天前未更新的播客
cutoff_date = date.today() - timedelta(days=7)
podcasts_to_scrape = await session.execute(
    select(Podcast)
    .outerjoin(
        PodcastDailyMetric,
        (Podcast.id == PodcastDailyMetric.podcast_id) &
        (PodcastDailyMetric.snapshot_date >= cutoff_date)
    )
    .where(PodcastDailyMetric.id.is_(None))
    .limit(1000)
)
```

### 方案C：优先级队列
根据播客的订阅数或重要性设置优先级：
- 高订阅数播客：每天更新
- 中等订阅数播客：每周更新
- 低订阅数播客：每月更新

## 🚀 手动触发

### 测试分批爬取
```python
from app.db.session import AsyncSessionFactory
from app.services.scraper_service import PodcastScraper
from app.services.anti_scraping import create_anti_scraping_manager

async with AsyncSessionFactory() as session:
    scraper = PodcastScraper(session, create_anti_scraping_manager())
    try:
        scrape_run = await scraper.scrape_podcasts_batch(
            batch_size=100,  # 测试时用较小的数量
            days_in_cycle=7
        )
        print(f"完成: {scrape_run.successful_count}/{scrape_run.total_podcasts}")
    finally:
        await scraper.close()
```

### 通过API触发
```bash
curl -X POST http://localhost:8000/api/scraper/run
```

## 📝 注意事项

1. **排名计算**：每天爬取完成后，会基于当天所有已爬取的播客计算排名
2. **数据一致性**：排名基于同一天的数据，保证一致性
3. **失败重试**：失败的播客会在下一个周期自动重试
4. **资源消耗**：每天约1000个播客，按3-6秒延迟，预计需要1-2小时完成

