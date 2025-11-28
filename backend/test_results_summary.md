# 订阅数抓取测试结果 - 10个播客链接

> 测试时间: 2025-01-XX
> 测试方法: 动态页面渲染 (Playwright)
> 成功率: 9/10 (90%)

---

## 测试链接列表

### 1. 天真不天真
- **链接**: https://www.xiaoyuzhoufm.com/podcast/65cef9e3cace72dff8d98de3
- **抓取到的订阅数**: 200
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 2. 凹凸电波
- **链接**: https://www.xiaoyuzhoufm.com/podcast/5e2839ca418a84a0462431b7
- **抓取到的订阅数**: 1,561,557
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 3. 文化有限
- **链接**: https://www.xiaoyuzhoufm.com/podcast/5e4515bd418a84a046e2b11a
- **抓取到的订阅数**: 1,280,820
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 4. 纵横四海
- **链接**: https://www.xiaoyuzhoufm.com/podcast/62694abdb221dd5908417d1e
- **抓取到的订阅数**: 1,344,728
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 5. 声动早咖啡
- **链接**: https://www.xiaoyuzhoufm.com/podcast/60de7c003dd577b40d5a40f3
- **抓取到的订阅数**: 1,456,162
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 6. 知行小酒馆
- **链接**: https://www.xiaoyuzhoufm.com/podcast/6013f9f58e2f7ee375cf4216
- **抓取到的订阅数**: 1,450,043
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 7. 随机波动StochasticVolatility
- **链接**: https://www.xiaoyuzhoufm.com/podcast/5e7cc741418a84a046b0c2bd
- **抓取到的订阅数**: 1,280,820
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 8. 忽左忽右
- **链接**: https://www.xiaoyuzhoufm.com/podcast/5e4ee557418a84a0466737b7
- **抓取到的订阅数**: 1,035,172
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 9. 岩中花述
- **链接**: https://www.xiaoyuzhoufm.com/podcast/625635587bfca4e73e990703
- **抓取到的订阅数**: 200
- **状态**: ✅ 成功
- **方法**: dynamic_rendering

### 10. 无人知晓
- **链接**: https://www.xiaoyuzhoufm.com/podcast/611719d3cb0b82e1df0ad29e
- **抓取到的订阅数**: N/A
- **状态**: ❌ 失败
- **方法**: 无

---

## 测试统计

- **总测试数**: 10
- **成功数**: 9
- **失败数**: 1
- **成功率**: 90%

## 方法统计

- **静态页面解析**: 0/10 (0.00%)
- **动态页面渲染**: 9/10 (90.00%)
- **API调用**: 0/10 (0.00%)

## 推荐方法

✅ **dynamic_rendering** (动态页面渲染) - 使用 Playwright 进行页面渲染和解析

---

## 注意事项

1. 部分播客（如"天真不天真"、"岩中花述"）抓取到的订阅数为200，可能需要进一步验证准确性
2. "无人知晓"播客抓取失败，需要检查原因
3. 所有成功的抓取都使用了 Playwright 动态渲染方法
4. 静态页面解析方法在当前测试中全部失败，说明页面内容主要由JavaScript动态生成

---

**请手动访问上述链接，验证抓取到的订阅数是否准确。**


