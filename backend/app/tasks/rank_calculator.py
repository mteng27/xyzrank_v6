"""排名计算任务

在每天最后一批抓取完成后，统一计算排名
"""
from datetime import date, timedelta
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionFactory
from app.services.scraper_service import PodcastScraper
from app.services.anti_scraping import create_anti_scraping_manager


async def calculate_daily_ranks():
    """计算昨天的排名（在今天的抓取完成后）"""
    logger.info("开始计算每日排名")
    async with AsyncSessionFactory() as session:
        anti_scraping = create_anti_scraping_manager()
        scraper = PodcastScraper(session, anti_scraping_manager=anti_scraping)
        try:
            # 计算昨天的排名（因为今天的抓取可能还在进行）
            target_date = date.today() - timedelta(days=1)
            await scraper.calculate_ranks(target_date)
            logger.info(f"完成 {target_date} 的排名计算")
        except Exception as e:
            logger.error(f"计算排名失败: {e}")
        finally:
            await scraper.close()

