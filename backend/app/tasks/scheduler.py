"""定时任务调度器"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import AsyncSessionFactory
from app.services.scraper_service import PodcastScraper


scheduler = AsyncIOScheduler()


async def daily_scrape_task_batch(batch_index: int, total_batches: int = 24):
    """
    每日分批抓取任务（分时段执行）
    
    策略：将7000个播客分成24批，每小时执行一批
    每批约292个播客，24小时完成所有播客
    
    Args:
        batch_index: 当前批次索引（0-23）
        total_batches: 总批次数（默认24）
    """
    logger.info(f"开始执行第 {batch_index + 1}/{total_batches} 批抓取任务")
    async with AsyncSessionFactory() as session:
        from app.services.anti_scraping import create_anti_scraping_manager
        from sqlalchemy import select
        from app.models.podcast import Podcast
        
        # 使用更保守的反爬虫配置（24小时完成，可以更慢更安全）
        optimized_config = {
            "rate_limiter": {
                "max_requests": 10,  # 每分钟10个请求（保守）
                "time_window": 60
            },
            "request_delay": {
                "min_delay": 3.0,    # 3-5秒延迟（保守）
                "max_delay": 5.0,
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
        
        anti_scraping = create_anti_scraping_manager(optimized_config)
        scraper = PodcastScraper(session, anti_scraping_manager=anti_scraping)
        try:
            # 获取所有播客
            result = await session.execute(select(Podcast))
            all_podcasts = result.scalars().all()
            
            # 计算每批的数量
            total_podcasts = len(all_podcasts)
            batch_size = (total_podcasts + total_batches - 1) // total_batches  # 向上取整
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, total_podcasts)
            
            podcasts_batch = all_podcasts[start_idx:end_idx]
            
            logger.info(
                f"批次 {batch_index + 1}/{total_batches}: "
                f"播客范围 {start_idx + 1}-{end_idx} (共 {len(podcasts_batch)} 个)"
            )
            
            # 使用每日抓取方法，但只处理当前批次
            # 24小时完成，可以使用更低的并发
            scrape_run = await scraper.scrape_all_podcasts_daily(
                max_concurrent=5,  # 更低并发（5个），更安全
                podcasts_to_scrape=podcasts_batch  # 只处理当前批次
            )
            
            # 注意：排名计算在最后一批完成后统一进行（由rank_calculator任务处理）
            # 这里不计算排名，避免重复计算
            
            logger.info(
                f"批次 {batch_index + 1}/{total_batches} 完成: "
                f"总数={scrape_run.total_podcasts}, "
                f"成功={scrape_run.successful_count}, "
                f"失败={scrape_run.failed_count}, "
                f"耗时={(scrape_run.completed_at - scrape_run.started_at).total_seconds() / 60:.1f} 分钟"
            )
        except Exception as e:
            logger.error(f"批次 {batch_index + 1} 抓取任务失败: {e}")
        finally:
            await scraper.close()


async def daily_scrape_task():
    """每日抓取任务（单次执行所有播客，低并发）"""
    logger.info("开始执行每日抓取任务（低并发模式）")
    async with AsyncSessionFactory() as session:
        from app.services.anti_scraping import create_anti_scraping_manager
        
        # 使用更保守的反爬虫配置（24小时完成，可以更慢更安全）
        optimized_config = {
            "rate_limiter": {
                "max_requests": 10,  # 每分钟10个请求（保守）
                "time_window": 60
            },
            "request_delay": {
                "min_delay": 3.0,    # 3-5秒延迟（保守）
                "max_delay": 5.0,
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
        
        anti_scraping = create_anti_scraping_manager(optimized_config)
        scraper = PodcastScraper(session, anti_scraping_manager=anti_scraping)
        try:
            # 使用低并发模式：每天完成所有7000个播客
            scrape_run = await scraper.scrape_all_podcasts_daily(
                max_concurrent=8  # 低并发（8个）
            )
            logger.info(
                f"每日抓取任务完成: "
                f"总数={scrape_run.total_podcasts}, "
                f"成功={scrape_run.successful_count}, "
                f"失败={scrape_run.failed_count}, "
                f"耗时={(scrape_run.completed_at - scrape_run.started_at).total_seconds() / 60:.1f} 分钟"
            )
        except Exception as e:
            logger.error(f"每日抓取任务失败: {e}")
        finally:
            await scraper.close()


def setup_scheduler():
    """设置定时任务"""
    # 方案C：分24批执行（每小时执行一批，24小时完成所有播客）
    # 策略：更保守的配置，24小时内完成即可
    total_batches = 24  # 24批，每小时一批
    
    for i in range(total_batches):
        hour = i  # 从0点开始，每小时一批
        scheduler.add_job(
            lambda batch_idx=i: daily_scrape_task_batch(batch_idx, total_batches),
            trigger=CronTrigger(hour=hour, minute=0),
            id=f"daily_scrape_batch_{i}",
            name=f"每日播客数据抓取（批次 {i+1}/{total_batches}）",
            replace_existing=True,
        )
        logger.info(f"定时任务已设置: 每天 {hour:02d}:00 执行第 {i+1}/{total_batches} 批抓取")
    
    # 在每天23:30计算排名（所有批次完成后）
    from app.tasks.rank_calculator import calculate_daily_ranks
    scheduler.add_job(
        calculate_daily_ranks,
        trigger=CronTrigger(hour=23, minute=30),
        id="calculate_daily_ranks",
        name="每日排名计算",
        replace_existing=True,
    )
    logger.info("定时任务已设置: 每天 23:30 计算排名")
    
    # 方案1：单次执行（已禁用，如需启用请取消注释）
    """
    scheduler.add_job(
        daily_scrape_task,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_scrape",
        name="每日播客数据抓取（单次）",
        replace_existing=True,
    )
    logger.info("定时任务已设置: 每天凌晨 2:00 执行播客数据抓取（单次，低并发）")
    """


def start_scheduler():
    """启动定时任务调度器"""
    setup_scheduler()
    scheduler.start()
    logger.info("定时任务调度器已启动")


def shutdown_scheduler():
    """关闭定时任务调度器"""
    scheduler.shutdown()
    logger.info("定时任务调度器已关闭")


