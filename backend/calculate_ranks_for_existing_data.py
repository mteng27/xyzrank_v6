"""为现有数据计算排名

这个脚本用于：
1. 运行数据库迁移（添加排名字段）
2. 为所有历史数据计算排名
"""
import asyncio
from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionFactory
from app.services.scraper_service import PodcastScraper
from app.services.anti_scraping import create_anti_scraping_manager
from loguru import logger

async def run_migration():
    """运行数据库迁移（添加排名字段）"""
    logger.info("运行数据库迁移...")
    try:
        async with AsyncSessionFactory() as session:
            # 检查字段是否已存在
            result = await session.execute(
                text("PRAGMA table_info(podcast_daily_metrics)")
            )
            columns = [row[1] for row in result.fetchall()]
            
            if 'global_rank' not in columns:
                logger.info("添加 global_rank 字段...")
                await session.execute(
                    text("ALTER TABLE podcast_daily_metrics ADD COLUMN global_rank INTEGER")
                )
                await session.commit()
                logger.info("✓ global_rank 字段已添加")
            
            if 'category_rank' not in columns:
                logger.info("添加 category_rank 字段...")
                await session.execute(
                    text("ALTER TABLE podcast_daily_metrics ADD COLUMN category_rank INTEGER")
                )
                await session.commit()
                logger.info("✓ category_rank 字段已添加")
            
            # 创建索引
            try:
                await session.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_podcast_daily_metrics_global_rank ON podcast_daily_metrics(global_rank)")
                )
                await session.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_podcast_daily_metrics_category_rank ON podcast_daily_metrics(category_rank)")
                )
                await session.commit()
                logger.info("✓ 索引已创建")
            except Exception as e:
                logger.warning(f"创建索引时出现警告（可能已存在）: {e}")
            
            logger.info("数据库迁移完成")
            return True
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        return False

async def calculate_all_ranks():
    """为所有历史数据计算排名"""
    logger.info("开始为所有历史数据计算排名...")
    
    async with AsyncSessionFactory() as session:
        scraper = PodcastScraper(session, create_anti_scraping_manager())
        try:
            # 获取所有有数据的日期
            result = await session.execute(
                text("SELECT DISTINCT snapshot_date FROM podcast_daily_metrics ORDER BY snapshot_date")
            )
            dates = [row[0] for row in result.fetchall()]
            
            logger.info(f"找到 {len(dates)} 个日期需要计算排名")
            
            for i, snapshot_date in enumerate(dates, 1):
                logger.info(f"[{i}/{len(dates)}] 计算 {snapshot_date} 的排名...")
                await scraper.calculate_ranks(snapshot_date)
            
            logger.success("所有日期的排名计算完成")
        finally:
            await scraper.close()

async def main():
    """主函数"""
    print("=" * 60)
    print("为现有数据计算排名")
    print("=" * 60)
    print()
    
    # 步骤1：运行迁移
    if not await run_migration():
        print("❌ 数据库迁移失败，请检查错误信息")
        return
    
    print()
    
    # 步骤2：计算排名
    await calculate_all_ranks()
    
    print()
    print("=" * 60)
    print("✅ 完成！")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())


