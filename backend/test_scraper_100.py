"""测试100个播客的抓取功能（带反爬虫策略）"""
import asyncio
import json
from datetime import datetime, date
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionFactory
from app.models.podcast import Podcast, PodcastDailyMetric
from app.services.scraper_service import PodcastScraper
from app.services.anti_scraping import create_anti_scraping_manager
from loguru import logger


class ScraperTester:
    """爬虫测试器"""
    
    def __init__(self, limit: int = 100):
        self.limit = limit
        self.results: List[Dict] = []
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "errors": {},
            "start_time": None,
            "end_time": None,
            "duration": None
        }
    
    async def test_single_podcast(
        self,
        scraper: PodcastScraper,
        podcast: Podcast,
        index: int,
        session: AsyncSession,
        save_to_db: bool = True
    ) -> Dict:
        """测试单个播客并保存到数据库"""
        result = {
            "index": index,
            "xyz_id": podcast.xyz_id,
            "name": podcast.name,
            "success": False,
            "subscriber_count": None,
            "saved_to_db": False,
            "error": None,
            "error_type": None
        }
        
        try:
            logger.info(f"[{index}/{self.limit}] 测试: {podcast.name} ({podcast.xyz_id})")
            subscriber_count = await scraper.scrape_subscriber_count(podcast.xyz_id)
            
            if subscriber_count is not None:
                result["success"] = True
                result["subscriber_count"] = subscriber_count
                logger.success(f"[{index}/{self.limit}] ✅ {podcast.name}: {subscriber_count:,} 订阅者")
                
                # 保存到数据库
                if save_to_db:
                    try:
                        today = date.today()
                        # 检查是否已存在今日数据
                        existing_metric = await session.execute(
                            select(PodcastDailyMetric).where(
                                PodcastDailyMetric.podcast_id == podcast.id,
                                PodcastDailyMetric.snapshot_date == today
                            )
                        )
                        existing = existing_metric.scalar_one_or_none()
                        
                        if existing:
                            # 更新现有记录
                            existing.subscriber_count = subscriber_count
                            logger.info(f"[{index}/{self.limit}] 📝 更新数据库记录: {podcast.name} ({subscriber_count:,})")
                        else:
                            # 创建新记录
                            metric = PodcastDailyMetric(
                                podcast_id=podcast.id,
                                snapshot_date=today,
                                subscriber_count=subscriber_count
                            )
                            session.add(metric)
                            logger.info(f"[{index}/{self.limit}] 💾 保存到数据库: {podcast.name} ({subscriber_count:,})")
                        
                        await session.commit()
                        result["saved_to_db"] = True
                    except Exception as db_error:
                        logger.error(f"[{index}/{self.limit}] ❌ 保存到数据库失败: {db_error}")
                        await session.rollback()
                        result["error"] = f"数据库保存失败: {db_error}"
            else:
                result["error"] = "未获取到订阅数"
                result["error_type"] = "no_data"
                logger.warning(f"[{index}/{self.limit}] ⚠️ {podcast.name}: 未获取到订阅数")
        
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            logger.error(f"[{index}/{self.limit}] ❌ {podcast.name}: {e}")
        
        return result
    
    async def test_batch(self, max_concurrent: int = 3) -> Dict:
        """批量测试"""
        self.stats["start_time"] = datetime.now()
        logger.info(f"开始测试 {self.limit} 个播客，并发数: {max_concurrent}")
        
        # 创建反爬虫管理器（使用保守策略）
        anti_scraping_config = {
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
        anti_scraping = create_anti_scraping_manager(anti_scraping_config)
        
        # 从数据库获取播客列表
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Podcast).limit(self.limit)
            )
            podcasts = result.scalars().all()
            self.stats["total"] = len(podcasts)
            logger.info(f"从数据库加载了 {len(podcasts)} 个播客")
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_with_semaphore(podcast: Podcast, index: int):
            async with semaphore:
                async with AsyncSessionFactory() as session:
                    scraper = PodcastScraper(session, anti_scraping_manager=anti_scraping)
                    try:
                        result = await self.test_single_podcast(
                            scraper, podcast, index, session, save_to_db=True
                        )
                        return result
                    finally:
                        await scraper.close()
        
        # 执行批量测试
        tasks = [
            test_with_semaphore(podcast, i + 1)
            for i, podcast in enumerate(podcasts)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.results.append({
                    "index": i + 1,
                    "xyz_id": podcasts[i].xyz_id if i < len(podcasts) else "N/A",
                    "name": podcasts[i].name if i < len(podcasts) else "N/A",
                    "success": False,
                    "error": str(result),
                    "error_type": type(result).__name__
                })
            else:
                self.results.append(result)
        
        # 统计
        self.stats["end_time"] = datetime.now()
        self.stats["duration"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        saved_count = 0
        for result in self.results:
            if result.get("success"):
                self.stats["successful"] += 1
                if result.get("saved_to_db"):
                    saved_count += 1
            else:
                self.stats["failed"] += 1
                error_type = result.get("error_type", "unknown")
                self.stats["errors"][error_type] = self.stats["errors"].get(error_type, 0) + 1
        
        self.stats["saved_to_db"] = saved_count
        
        return self.stats
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        report = {
            "test_info": {
                "total_tested": self.stats["total"],
                "successful": self.stats["successful"],
                "failed": self.stats["failed"],
                "saved_to_db": self.stats.get("saved_to_db", 0),
                "success_rate": f"{self.stats['successful']/self.stats['total']*100:.2f}%" if self.stats["total"] > 0 else "0%",
                "duration_seconds": self.stats["duration"],
                "duration_formatted": f"{int(self.stats['duration']//60)}分{int(self.stats['duration']%60)}秒" if self.stats["duration"] else None,
                "avg_time_per_request": f"{self.stats['duration']/self.stats['total']:.2f}秒" if self.stats["total"] > 0 and self.stats["duration"] else None
            },
            "error_statistics": self.stats["errors"],
            "sample_results": {
                "successful": [r for r in self.results if r.get("success")][:10],
                "failed": [r for r in self.results if not r.get("success")][:10]
            },
            "subscriber_count_stats": self._calculate_subscriber_stats()
        }
        return report
    
    def _calculate_subscriber_stats(self) -> Dict:
        """计算订阅数统计"""
        successful_results = [r for r in self.results if r.get("success") and r.get("subscriber_count")]
        if not successful_results:
            return {}
        
        counts = [r["subscriber_count"] for r in successful_results]
        return {
            "count": len(counts),
            "min": min(counts),
            "max": max(counts),
            "avg": int(sum(counts) / len(counts)),
            "median": sorted(counts)[len(counts) // 2]
        }


async def main():
    """主函数"""
    print("="*80)
    print("播客订阅数抓取测试 - 100个播客")
    print("="*80)
    print()
    print("配置:")
    print("  - 测试数量: 100个播客")
    print("  - 并发数: 3个")
    print("  - 反爬虫策略: 每分钟10个请求，3-6秒延迟")
    print()
    
    tester = ScraperTester(limit=100)
    
    try:
        # 执行测试
        stats = await tester.test_batch(max_concurrent=3)
        
        # 生成报告
        print("\n" + "="*80)
        print("测试报告")
        print("="*80)
        report = tester.generate_report()
        
        print(f"\n📊 测试统计:")
        print(f"  总测试数: {report['test_info']['total_tested']}")
        print(f"  成功数: {report['test_info']['successful']}")
        print(f"  失败数: {report['test_info']['failed']}")
        print(f"  成功率: {report['test_info']['success_rate']}")
        print(f"  保存到数据库: {stats.get('saved_to_db', 0)} 条")
        print(f"  总耗时: {report['test_info']['duration_formatted']}")
        print(f"  平均耗时: {report['test_info']['avg_time_per_request']} / 请求")
        
        if report['error_statistics']:
            print(f"\n❌ 错误统计:")
            for error_type, count in report['error_statistics'].items():
                print(f"  {error_type}: {count} 次")
        
        if report['subscriber_count_stats']:
            stats = report['subscriber_count_stats']
            print(f"\n📈 订阅数统计:")
            print(f"  有效数据: {stats['count']} 个")
            print(f"  最小值: {stats['min']:,}")
            print(f"  最大值: {stats['max']:,}")
            print(f"  平均值: {stats['avg']:,}")
            print(f"  中位数: {stats['median']:,}")
        
        # 保存详细结果
        output_file = "scraper_100_test_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "test_time": datetime.now().isoformat(),
                "report": report,
                "detailed_results": tester.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细结果已保存到: {output_file}")
        
        # 显示成功和失败示例
        if report['sample_results']['successful']:
            print(f"\n✅ 成功示例（前5个）:")
            for r in report['sample_results']['successful'][:5]:
                print(f"  - {r['name']}: {r['subscriber_count']:,} 订阅者")
        
        if report['sample_results']['failed']:
            print(f"\n❌ 失败示例（前5个）:")
            for r in report['sample_results']['failed'][:5]:
                print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")
        
        # 检查是否有被封禁的迹象
        http_errors = {
            k: v for k, v in report['error_statistics'].items()
            if '403' in k or '429' in k or 'Forbidden' in k or 'TooManyRequests' in k
        }
        if http_errors:
            print(f"\n⚠️  警告: 检测到可能的封禁迹象!")
            print(f"  错误类型: {http_errors}")
            print(f"  建议: 降低请求频率或增加延迟")
        else:
            print(f"\n✅ 未检测到封禁迹象，反爬虫策略正常工作")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

