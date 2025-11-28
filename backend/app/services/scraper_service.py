"""播客数据爬虫服务 - 从小宇宙平台抓取播客数据"""
from datetime import date, datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from httpx import AsyncClient
from bs4 import BeautifulSoup
from loguru import logger

from app.models.podcast import Podcast, PodcastDailyMetric, ScrapeRun
from app.services.anti_scraping import AntiScrapingManager, create_anti_scraping_manager


class PodcastScraper:
    """播客数据爬虫"""
    
    def __init__(
        self,
        session: AsyncSession,
        anti_scraping_manager: Optional[AntiScrapingManager] = None
    ):
        """
        Args:
            session: 数据库会话
            anti_scraping_manager: 反爬虫管理器，如果为 None 则创建默认管理器
        """
        self.session = session
        self.anti_scraping = anti_scraping_manager or create_anti_scraping_manager()
        # 使用反爬虫管理器生成的请求头
        headers = self.anti_scraping.get_headers()
        self.client = AsyncClient(timeout=30.0, follow_redirects=True, headers=headers)
        self.browser_context = None  # 用于Playwright的浏览器上下文
    
    async def scrape_podcast_info(self, xyz_id: str) -> Optional[dict]:
        """
        抓取播客基本信息
        
        Args:
            xyz_id: 小宇宙播客 ID
        
        Returns:
            播客信息字典，如果失败返回 None
        """
        url = f"https://www.xiaoyuzhoufm.com/podcast/{xyz_id}"
        
        for attempt in self.anti_scraping.retry_attempts():
            try:
                await self.anti_scraping.acquire_slot()  # 频率限制
                await self.anti_scraping.apply_delay()  # 应用请求延迟
                
                response = await self.client.get(url, headers=self.anti_scraping.get_random_headers())
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                info = {
                    "name": None,
                    "rss_url": None,
                    "cover_url": None,
                    "category": None,
                    "description": None,
                }
                
                title_tag = soup.find("title")
                if title_tag:
                    info["name"] = title_tag.get_text().strip()
                
                rss_link = soup.find("link", {"type": "application/rss+xml"})
                if rss_link:
                    info["rss_url"] = rss_link.get("href")
                
                og_image = soup.find("meta", {"property": "og:image"})
                if og_image:
                    info["cover_url"] = og_image.get("content")
                
                description_tag = soup.find("meta", {"name": "description"})
                if description_tag:
                    info["description"] = description_tag.get("content")
                
                logger.info(f"成功抓取播客 {xyz_id} 的信息")
                return info
                
            except Exception as e:
                logger.warning(f"抓取播客 {xyz_id} 信息失败 (尝试 {attempt}/{self.anti_scraping.max_retries}): {e}")
                await self.anti_scraping.handle_retry(attempt)
        
        logger.error(f"抓取播客 {xyz_id} 信息失败，已达最大重试次数")
        return None
    
    async def scrape_subscriber_count(self, xyz_id: str) -> Optional[int]:
        """
        抓取播客订阅者数量
        
        Args:
            xyz_id: 小宇宙播客 ID
        
        Returns:
            订阅者数量，如果失败返回 None
        """
        url = f"https://www.xiaoyuzhoufm.com/podcast/{xyz_id}"
        
        for attempt in self.anti_scraping.retry_attempts():
            try:
                await self.anti_scraping.acquire_slot()  # 频率限制
                
                # 尝试使用 Playwright 获取动态渲染内容
                try:
                    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
                    
                    if not self.browser_context:
                        pw = await async_playwright().start()
                        browser = await pw.chromium.launch(headless=True)
                        self.browser_context = await browser.new_context()
                    
                    page = await self.browser_context.new_page()
                    await page.set_extra_http_headers(self.anti_scraping.get_random_headers())
                    
                    await self.anti_scraping.apply_delay()  # 应用请求延迟
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    html_content = await page.content()
                    await page.close()
                    
                    from bs4 import BeautifulSoup
                    import re
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # 优化解析逻辑：查找包含"已订阅"的文本，并从其父元素中提取数字
                    subscriber_elements = soup.find_all(string=re.compile(r'已订阅', re.I))
                    
                    found_numbers = []
                    for elem in subscriber_elements:
                        parent_text = elem.find_parent().get_text(separator=" ", strip=True) if elem.find_parent() else str(elem)
                        
                        # 优先匹配紧挨着的格式，例如 "1450035已订阅"
                        tight_match = re.search(r'(\d{4,})已订阅', parent_text)
                        if tight_match:
                            num = int(tight_match.group(1))
                            if 1000 <= num < 100000000:  # 确保数字在合理范围内
                                found_numbers.append(num)
                                logger.debug(f"从紧凑格式提取到订阅数: {num}")
                                continue
                        
                        # 备用：匹配有空格的情况，例如 "1,450,035 已订阅"
                        space_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s+已订阅', parent_text)
                        if space_match:
                            num = int(space_match.group(1).replace(',', ''))
                            if 1000 <= num < 100000000:
                                found_numbers.append(num)
                                logger.debug(f"从带空格格式提取到订阅数: {num}")
                                continue
                    
                    if found_numbers:
                        # 返回找到的最大订阅数
                        max_subscribers = max(found_numbers)
                        logger.info(f"通过Playwright成功抓取播客 {xyz_id} 订阅数: {max_subscribers:,}")
                        return max_subscribers
                    
                except ImportError:
                    logger.warning("Playwright未安装，无法使用动态渲染方式")
                except (PlaywrightTimeoutError, PlaywrightError) as e:
                    logger.warning(f"Playwright抓取失败: {e}")
                
                # 如果Playwright失败，尝试静态抓取
                response = await self.client.get(url, headers=self.anti_scraping.get_random_headers())
                response.raise_for_status()
                
                from bs4 import BeautifulSoup
                import re
                soup = BeautifulSoup(response.text, "html.parser")
                
                subscriber_elements = soup.find_all(string=re.compile(r'已订阅', re.I))
                
                found_numbers = []
                for elem in subscriber_elements:
                    parent_text = elem.find_parent().get_text(separator=" ", strip=True) if elem.find_parent() else str(elem)
                    
                    tight_match = re.search(r'(\d{4,})已订阅', parent_text)
                    if tight_match:
                        num = int(tight_match.group(1))
                        if 1000 <= num < 100000000:
                            found_numbers.append(num)
                            continue
                    
                    space_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s+已订阅', parent_text)
                    if space_match:
                        num = int(space_match.group(1).replace(',', ''))
                        if 1000 <= num < 100000000:
                            found_numbers.append(num)
                            continue
                
                if found_numbers:
                    max_subscribers = max(found_numbers)
                    logger.info(f"通过静态解析成功抓取播客 {xyz_id} 订阅数: {max_subscribers:,}")
                    return max_subscribers
                
                logger.warning(f"未能在页面中找到播客 {xyz_id} 的订阅数")
                return None
                
            except Exception as e:
                logger.warning(f"抓取播客 {xyz_id} 订阅者数量失败 (尝试 {attempt}/{self.anti_scraping.max_retries}): {e}")
                await self.anti_scraping.handle_retry(attempt)
        
        logger.error(f"抓取播客 {xyz_id} 订阅者数量失败，已达最大重试次数")
        return None
    
    async def update_podcast_from_scrape(self, podcast: Podcast) -> bool:
        """
        从爬取的数据更新播客信息
        
        Args:
            podcast: 播客对象
        
        Returns:
            是否成功更新
        """
        info = await self.scrape_podcast_info(podcast.xyz_id)
        if not info:
            return False
        
        updated = False
        for key, value in info.items():
            if value and getattr(podcast, key) != value:
                setattr(podcast, key, value)
                updated = True
        
        if updated:
            await self.session.commit()
            logger.info(f"更新播客 {podcast.xyz_id} 的信息")
        
        return updated
    
    async def calculate_ranks(self, snapshot_date: date) -> None:
        """
        计算指定日期的所有播客排名（全站排名和分类排名）
        
        Args:
            snapshot_date: 快照日期
        """
        logger.info(f"开始计算 {snapshot_date} 的排名...")
        
        # 获取该日期所有有订阅数的指标
        metrics_query = (
            select(PodcastDailyMetric)
            .where(
                PodcastDailyMetric.snapshot_date == snapshot_date,
                PodcastDailyMetric.subscriber_count.isnot(None)
            )
            .order_by(desc(PodcastDailyMetric.subscriber_count))
        )
        metrics_result = await self.session.execute(metrics_query)
        metrics = metrics_result.scalars().all()
        
        if not metrics:
            logger.warning(f"日期 {snapshot_date} 没有指标数据，跳过排名计算")
            return
        
        # 计算全站排名
        global_rank = 1
        for metric in metrics:
            metric.global_rank = global_rank
            global_rank += 1
        
        # 按分类计算排名
        # 获取所有分类
        categories_query = (
            select(Podcast.category)
            .distinct()
            .where(Podcast.category.isnot(None))
        )
        categories_result = await self.session.execute(categories_query)
        categories = [row[0] for row in categories_result.all()]
        
        for category in categories:
            # 获取该分类下该日期的所有指标
            category_metrics_query = (
                select(PodcastDailyMetric)
                .join(Podcast, PodcastDailyMetric.podcast_id == Podcast.id)
                .where(
                    Podcast.category == category,
                    PodcastDailyMetric.snapshot_date == snapshot_date,
                    PodcastDailyMetric.subscriber_count.isnot(None)
                )
                .order_by(desc(PodcastDailyMetric.subscriber_count))
            )
            category_metrics_result = await self.session.execute(category_metrics_query)
            category_metrics = category_metrics_result.scalars().all()
            
            # 计算分类排名
            category_rank = 1
            for metric in category_metrics:
                metric.category_rank = category_rank
                category_rank += 1
        
        await self.session.commit()
        logger.info(f"完成 {snapshot_date} 的排名计算，共 {len(metrics)} 个播客")
    
    async def record_daily_metric(
        self,
        podcast_id: int,
        snapshot_date: date,
        subscriber_count: int,
    ) -> PodcastDailyMetric:
        """
        记录每日指标（不计算排名，排名在批量抓取后统一计算）
        
        Args:
            podcast_id: 播客 ID
            snapshot_date: 快照日期
            subscriber_count: 订阅者数量
        
        Returns:
            创建的指标对象
        """
        # 检查是否已存在
        result = await self.session.execute(
            select(PodcastDailyMetric).where(
                PodcastDailyMetric.podcast_id == podcast_id,
                PodcastDailyMetric.snapshot_date == snapshot_date
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.subscriber_count = subscriber_count
            # 清空排名，等待统一计算
            existing.global_rank = None
            existing.category_rank = None
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        
        metric = PodcastDailyMetric(
            podcast_id=podcast_id,
            snapshot_date=snapshot_date,
            subscriber_count=subscriber_count,
            global_rank=None,  # 排名稍后统一计算
            category_rank=None
        )
        self.session.add(metric)
        await self.session.commit()
        await self.session.refresh(metric)
        return metric
    
    async def scrape_all_podcasts_daily(
        self,
        max_concurrent: int = 8,
        podcasts_to_scrape: Optional[list] = None
    ) -> ScrapeRun:
        """
        每天完成所有播客的爬取（低并发、分时段策略）
        
        策略：
        1. 低并发（默认8个并发，降低封禁风险）
        2. 优化延迟（保持合理延迟，但稍微优化）
        3. 支持分批执行（可以分时段调用）
        
        Args:
            max_concurrent: 最大并发数（默认8，建议5-10）
            podcasts_to_scrape: 要抓取的播客列表（None表示抓取所有）
        
        Returns:
            爬取运行记录
        """
        import asyncio
        
        scrape_run = ScrapeRun(
            status="running",
            started_at=datetime.now()
        )
        self.session.add(scrape_run)
        await self.session.commit()
        await self.session.refresh(scrape_run)
        
        try:
            today = date.today()
            
            # 获取要抓取的播客列表
            if podcasts_to_scrape is None:
                result = await self.session.execute(select(Podcast))
                all_podcasts = result.scalars().all()
            else:
                all_podcasts = podcasts_to_scrape
            
            scrape_run.total_podcasts = len(all_podcasts)
            successful_count = 0
            failed_count = 0
            
            logger.info(
                f"开始每日抓取: 共 {len(all_podcasts)} 个播客, "
                f"并发数: {max_concurrent}"
            )
            
            # 使用信号量控制并发
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def scrape_one_podcast(podcast: Podcast, index: int):
                """抓取单个播客"""
                nonlocal successful_count, failed_count
                async with semaphore:
                    try:
                        if index % 100 == 0:
                            logger.info(f"进度: {index}/{len(all_podcasts)} (成功: {successful_count}, 失败: {failed_count})")
                        
                        # 只抓取订阅数，不更新播客信息（减少请求）
                        subscriber_count = await self.scrape_subscriber_count(podcast.xyz_id)
                        if subscriber_count is not None:
                            await self.record_daily_metric(
                                podcast.id,
                                today,
                                subscriber_count
                            )
                            successful_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"处理播客 {podcast.xyz_id} 时出错: {e}")
            
            # 并发执行所有任务
            tasks = [
                scrape_one_podcast(podcast, i + 1)
                for i, podcast in enumerate(all_podcasts)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 注意：排名计算在最后一批完成后统一进行（由rank_calculator任务处理）
            # 这里不计算排名，避免重复计算
            
            scrape_run.status = "completed"
            scrape_run.completed_at = datetime.now()
            scrape_run.successful_count = successful_count
            scrape_run.failed_count = failed_count
            
        except Exception as e:
            scrape_run.status = "failed"
            scrape_run.completed_at = datetime.now()
            scrape_run.error_message = str(e)
            logger.error(f"每日全量抓取失败: {e}")
        
        await self.session.commit()
        await self.session.refresh(scrape_run)
        return scrape_run
    
    async def scrape_podcasts_batch(
        self,
        batch_size: int = 1000,
        days_in_cycle: int = 7
    ) -> ScrapeRun:
        """
        分批抓取播客数据（用于一周内完成所有播客的爬取）
        
        策略：基于日期和播客ID的哈希值，每天爬取不同的播客
        例如：7天周期，每天爬取约 1/7 的播客
        
        Args:
            batch_size: 每批抓取的播客数量（默认1000，约7000/7）
            days_in_cycle: 完成一个完整周期需要的天数（默认7天）
        
        Returns:
            爬取运行记录
        """
        scrape_run = ScrapeRun(
            status="running",
            started_at=datetime.now()
        )
        self.session.add(scrape_run)
        await self.session.commit()
        await self.session.refresh(scrape_run)
        
        try:
            today = date.today()
            # 计算今天是周期中的第几天（0-6）
            day_of_cycle = today.toordinal() % days_in_cycle
            
            # 获取所有播客
            result = await self.session.execute(select(Podcast))
            all_podcasts = result.scalars().all()
            
            # 根据播客ID的哈希值筛选今天要爬取的播客
            podcasts_to_scrape = [
                p for p in all_podcasts
                if hash(p.id) % days_in_cycle == day_of_cycle
            ]
            
            # 如果筛选后的数量少于batch_size，取前batch_size个
            if len(podcasts_to_scrape) > batch_size:
                podcasts_to_scrape = podcasts_to_scrape[:batch_size]
            
            scrape_run.total_podcasts = len(podcasts_to_scrape)
            successful_count = 0
            failed_count = 0
            
            logger.info(
                f"开始分批抓取: 今天({today})是周期第{day_of_cycle}天, "
                f"将抓取 {len(podcasts_to_scrape)} 个播客"
            )
            
            # 第一步：抓取播客的订阅数
            for i, podcast in enumerate(podcasts_to_scrape, 1):
                try:
                    if i % 100 == 0:
                        logger.info(f"进度: {i}/{len(podcasts_to_scrape)}")
                    
                    # 更新播客信息（可选，减少请求）
                    # await self.update_podcast_from_scrape(podcast)
                    
                    # 抓取订阅者数量
                    subscriber_count = await self.scrape_subscriber_count(podcast.xyz_id)
                    if subscriber_count is not None:
                        await self.record_daily_metric(
                            podcast.id,
                            today,
                            subscriber_count
                        )
                        successful_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"处理播客 {podcast.xyz_id} 时出错: {e}")
            
            # 第二步：统一计算排名（基于今天所有已爬取的播客）
            logger.info("开始计算排名...")
            await self.calculate_ranks(today)
            
            scrape_run.status = "completed"
            scrape_run.completed_at = datetime.now()
            scrape_run.successful_count = successful_count
            scrape_run.failed_count = failed_count
            
        except Exception as e:
            scrape_run.status = "failed"
            scrape_run.completed_at = datetime.now()
            scrape_run.error_message = str(e)
            logger.error(f"分批抓取失败: {e}")
        
        await self.session.commit()
        await self.session.refresh(scrape_run)
        return scrape_run
    
    async def scrape_all_podcasts(self) -> ScrapeRun:
        """
        抓取所有播客的数据，并在完成后计算排名
        
        Returns:
            爬取运行记录
        """
        scrape_run = ScrapeRun(
            status="running",
            started_at=datetime.now()
        )
        self.session.add(scrape_run)
        await self.session.commit()
        await self.session.refresh(scrape_run)
        
        try:
            # 获取所有播客
            result = await self.session.execute(select(Podcast))
            podcasts = result.scalars().all()
            
            scrape_run.total_podcasts = len(podcasts)
            successful_count = 0
            failed_count = 0
            today = date.today()
            
            # 第一步：抓取所有播客的订阅数
            for podcast in podcasts:
                try:
                    # 更新播客信息
                    await self.update_podcast_from_scrape(podcast)
                    
                    # 抓取订阅者数量
                    subscriber_count = await self.scrape_subscriber_count(podcast.xyz_id)
                    if subscriber_count is not None:
                        await self.record_daily_metric(
                            podcast.id,
                            today,
                            subscriber_count
                        )
                        successful_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"处理播客 {podcast.xyz_id} 时出错: {e}")
            
            # 第二步：统一计算排名
            logger.info("开始计算排名...")
            await self.calculate_ranks(today)
            
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
    
    async def close(self):
        """关闭 HTTP 客户端和 Playwright 浏览器上下文"""
        await self.client.aclose()
        if self.browser_context:
            await self.browser_context.browser.close()
            self.browser_context = None
