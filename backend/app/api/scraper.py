"""爬虫相关 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db_session
from app.models.podcast import Podcast, ScrapeRun
from app.services.scraper_service import PodcastScraper
from pydantic import BaseModel


router = APIRouter(prefix="/api/scraper", tags=["scraper"])


class ScrapeRunResponse(BaseModel):
    id: int
    started_at: str
    completed_at: str | None
    status: str
    total_podcasts: int | None
    successful_count: int | None
    failed_count: int | None
    error_message: str | None

    class Config:
        from_attributes = True


@router.post("/run", response_model=ScrapeRunResponse)
async def run_scrape(session: AsyncSession = Depends(get_db_session)):
    """执行一次完整的播客数据抓取"""
    scraper = PodcastScraper(session)
    try:
        scrape_run = await scraper.scrape_all_podcasts()
        return scrape_run
    finally:
        await scraper.close()


@router.post("/podcast/{podcast_id}")
async def scrape_single_podcast(
    podcast_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """抓取单个播客的数据"""
    result = await session.execute(
        select(Podcast).where(Podcast.id == podcast_id)
    )
    podcast = result.scalar_one_or_none()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    scraper = PodcastScraper(session)
    try:
        updated = await scraper.update_podcast_from_scrape(podcast)
        return {
            "status": "completed",
            "podcast_id": podcast_id,
            "podcast_name": podcast.name,
            "updated": updated,
            "message": f"成功更新播客 {podcast.name}" if updated else f"播客 {podcast.name} 信息无需更新"
        }
    finally:
        await scraper.close()


@router.get("/runs", response_model=list[ScrapeRunResponse])
async def list_scrape_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
):
    """获取爬取运行历史"""
    from sqlalchemy import desc
    result = await session.execute(
        select(ScrapeRun).order_by(desc(ScrapeRun.started_at)).limit(limit)
    )
    return result.scalars().all()


