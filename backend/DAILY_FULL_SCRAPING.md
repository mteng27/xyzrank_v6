# 每日全量爬取策略

## 🎯 目标

**每天完成所有7000个播客的订阅数更新**

## 📊 性能计算

### 当前优化配置
- **并发数**: 20个
- **请求频率**: 每分钟30个请求
- **延迟**: 1.5-3秒（平均2秒）
- **总播客数**: 约7000个

### 时间估算

**理论计算**：
- 每分钟30个请求 × 60分钟 = 每小时1800个
- 7000 ÷ 1800 ≈ **3.9小时**

**实际计算（考虑并发）**：
- 20个并发，每个请求平均2秒
- 7000 ÷ 20 = 350批
- 350批 × 2秒 = 700秒 ≈ **11.7分钟**（纯请求时间）
- 加上网络延迟、处理时间等，预计 **1-2小时** 完成

## ⚙️ 配置说明

### 优化后的反爬虫配置

```python
optimized_config = {
    "rate_limiter": {
        "max_requests": 30,  # 每分钟30个请求（从10提高到30）
        "time_window": 60
    },
    "request_delay": {
        "min_delay": 1.5,    # 1.5-3秒延迟（从3-6秒降低）
        "max_delay": 3.0,
        "base_delay": 2.0
    },
    "retry_strategy": {
        "max_attempts": 3,
        "initial_delay": 1.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": True
    }
}
```

### 并发配置

```python
scrape_run = await scraper.scrape_all_podcasts_daily(
    max_concurrent=20,  # 并发数（可调整：10-30）
    use_aggressive_mode=True
)
```

## 🔧 调整建议

### 如果速度太慢

1. **提高并发数**（谨慎）：
   ```python
   max_concurrent=30  # 从20提高到30
   ```

2. **提高请求频率**（更谨慎）：
   ```python
   "max_requests": 40,  # 从30提高到40
   ```

3. **降低延迟**（最谨慎）：
   ```python
   "min_delay": 1.0,    # 从1.5降低到1.0
   "max_delay": 2.0,    # 从3.0降低到2.0
   ```

### 如果遇到封禁

1. **降低并发数**：
   ```python
   max_concurrent=10  # 从20降低到10
   ```

2. **降低请求频率**：
   ```python
   "max_requests": 20,  # 从30降低到20
   ```

3. **增加延迟**：
   ```python
   "min_delay": 2.0,    # 从1.5提高到2.0
   "max_delay": 4.0,    # 从3.0提高到4.0
   ```

## 📅 执行时间

### 默认时间
- **每天凌晨 2:00** 执行
- 预计 **1-2小时** 完成

### 修改执行时间

在 `scheduler.py` 中修改：
```python
scheduler.add_job(
    daily_scrape_task,
    trigger=CronTrigger(hour=2, minute=0),  # 修改这里
    ...
)
```

### 分时段执行（可选）

如果担心一次性执行时间太长，可以分多个时段：

```python
# 凌晨2点：前3500个
# 中午12点：后3500个

scheduler.add_job(
    daily_scrape_task_first_half,
    trigger=CronTrigger(hour=2, minute=0),
    ...
)

scheduler.add_job(
    daily_scrape_task_second_half,
    trigger=CronTrigger(hour=12, minute=0),
    ...
)
```

## 🚨 注意事项

### 1. 监控请求频率
- 观察日志中的错误率
- 如果出现大量429（Too Many Requests）或403（Forbidden），立即降低频率

### 2. IP封禁风险
- 虽然使用了反爬虫策略，但每天7000个请求仍然有风险
- 建议：
  - 使用代理池（如果可能）
  - 监控IP状态
  - 准备降级方案

### 3. 服务器资源
- 20个并发需要足够的网络带宽
- Playwright会消耗较多内存
- 确保服务器有足够资源

## 📈 监控指标

### 关键指标
- **成功率**: 应该 > 95%
- **平均耗时**: 每个播客 < 5秒
- **总耗时**: 完成7000个 < 2小时
- **错误类型**: 监控429、403等错误

### 日志示例
```
开始每日全量抓取: 共 7202 个播客, 并发数: 20
进度: 100/7202 (成功: 98, 失败: 2)
进度: 200/7202 (成功: 195, 失败: 5)
...
每日全量抓取任务完成: 总数=7202, 成功=7150, 失败=52, 耗时=85.3 分钟
```

## 🔄 降级方案

如果遇到问题，可以临时切换回分批爬取：

```python
# 在 scheduler.py 中临时切换
scrape_run = await scraper.scrape_podcasts_batch(
    batch_size=1000,
    days_in_cycle=7
)
```

## 💡 最佳实践

1. **首次运行**：使用较低的并发数（10-15）测试
2. **逐步提高**：确认稳定后，逐步提高并发数
3. **监控日志**：密切关注错误率和响应时间
4. **准备降级**：随时准备切换回保守策略

