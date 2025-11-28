from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db_session
from app.models.podcast import Podcast, PodcastDailyMetric
from pydantic import BaseModel

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


class TrendData(BaseModel):
    """趋势数据"""
    date: str
    subscriber_count: int

class PodcastResponse(BaseModel):
    id: int
    xyz_id: str
    name: str
    rss_url: Optional[str]
    cover_url: Optional[str]
    category: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str
    subscriber_count: Optional[int] = None  # 最新订阅数
    trend: Optional[List[TrendData]] = None  # 增长趋势数据
    rank: Optional[int] = None  # 全局订阅排名
    category_rank: Optional[int] = None  # 分类内排名

    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """自定义ORM转换，处理datetime对象"""
        data = {
            'id': obj.id,
            'xyz_id': obj.xyz_id,
            'name': obj.name,
            'rss_url': obj.rss_url,
            'cover_url': obj.cover_url,
            'category': obj.category,
            'description': obj.description,
            'created_at': str(obj.created_at) if obj.created_at else '',
            'updated_at': str(obj.updated_at) if obj.updated_at else '',
        }
        return cls(**data)


class PodcastCreate(BaseModel):
    xyz_id: str
    name: str
    rss_url: Optional[str] = None
    cover_url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class PodcastUpdate(BaseModel):
    name: Optional[str] = None
    rss_url: Optional[str] = None
    cover_url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class DailyMetricResponse(BaseModel):
    id: int
    podcast_id: int
    snapshot_date: str
    subscriber_count: int
    created_at: str

    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """自定义ORM转换，处理datetime和date对象"""
        data = {
            'id': obj.id,
            'podcast_id': obj.podcast_id,
            'snapshot_date': str(obj.snapshot_date) if obj.snapshot_date else '',
            'subscriber_count': obj.subscriber_count,
            'created_at': str(obj.created_at) if obj.created_at else '',
        }
        return cls(**data)


class DailyMetricCreate(BaseModel):
    snapshot_date: date
    subscriber_count: int


@router.get("/", response_model=List[PodcastResponse])
async def list_podcasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    search: Optional[str] = Query(None, description="搜索播客名称"),
    sort_by: str = Query("subscribers", description="排序方式: subscribers(订阅数), created(创建时间)"),
    session: AsyncSession = Depends(get_db_session),
):
    """获取播客列表，支持按订阅数排序和搜索
    
    注意：默认显示昨天的数据，因为今天的抓取可能还在进行中
    """
    from sqlalchemy import func
    from datetime import timedelta
    
    # 默认使用昨天的日期（如果今天的数据还在抓取中）
    target_date = date.today() - timedelta(days=1)
    
    # 获取每个播客在目标日期及之前的最新指标（包含订阅数和排名）
    latest_metrics_subq = (
        select(
            PodcastDailyMetric.podcast_id,
            func.max(PodcastDailyMetric.snapshot_date).label('latest_date')
        )
        .where(PodcastDailyMetric.snapshot_date <= target_date)  # 只取目标日期及之前的数据
        .group_by(PodcastDailyMetric.podcast_id)
        .subquery()
    )
    
    # 获取最新指标（包含订阅数、全站排名、分类排名）
    latest_metrics_subq_full = (
        select(
            PodcastDailyMetric.podcast_id,
            PodcastDailyMetric.subscriber_count,
            PodcastDailyMetric.global_rank,
            PodcastDailyMetric.category_rank
        )
        .join(
            latest_metrics_subq,
            (PodcastDailyMetric.podcast_id == latest_metrics_subq.c.podcast_id) &
            (PodcastDailyMetric.snapshot_date == latest_metrics_subq.c.latest_date)
        )
        .subquery()
    )
    
    # 主查询：连接播客和最新指标
    query = (
        select(
            Podcast,
            latest_metrics_subq_full.c.subscriber_count.label('subscriber_count'),
            latest_metrics_subq_full.c.global_rank.label('global_rank'),
            latest_metrics_subq_full.c.category_rank.label('category_rank')
        )
        .outerjoin(
            latest_metrics_subq_full,
            Podcast.id == latest_metrics_subq_full.c.podcast_id
        )
    )
    
    if category:
        query = query.where(Podcast.category == category)
    
    # 搜索功能
    if search:
        search_term = f"%{search}%"
        query = query.where(Podcast.name.like(search_term))
    
    # 排序：默认按订阅数排序
    query = query.order_by(desc(latest_metrics_subq_full.c.subscriber_count))
    
    # 应用筛选和分页
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    rows = result.all()
    
    # 获取趋势数据（批量查询以提高性能，只取目标日期及之前的数据）
    podcast_ids = [p.id for p, _, _, _ in rows]
    trends_map = {}
    
    if podcast_ids:
        # 批量获取所有播客的趋势数据（只取目标日期及之前）
        trends_query = (
            select(PodcastDailyMetric)
            .where(
                PodcastDailyMetric.podcast_id.in_(podcast_ids),
                PodcastDailyMetric.snapshot_date <= target_date
            )
            .order_by(PodcastDailyMetric.podcast_id, PodcastDailyMetric.snapshot_date)
        )
        trends_result = await session.execute(trends_query)
        trends_data = trends_result.scalars().all()
        
        # 按播客ID分组
        for metric in trends_data:
            if metric.podcast_id not in trends_map:
                trends_map[metric.podcast_id] = []
            trends_map[metric.podcast_id].append({
                'date': str(metric.snapshot_date),
                'subscriber_count': metric.subscriber_count
            })
    
    # 转换为响应格式（从数据库读取排名）
    return [
        PodcastResponse(
            id=p.id,
            xyz_id=p.xyz_id,
            name=p.name,
            rss_url=p.rss_url,
            cover_url=p.cover_url,
            category=p.category,
            description=p.description,
            created_at=str(p.created_at) if p.created_at else '',
            updated_at=str(p.updated_at) if p.updated_at else '',
            subscriber_count=subscriber_count,
            trend=trends_map.get(p.id, []),
            rank=global_rank,  # 从数据库读取的全站排名
            category_rank=category_rank,  # 从数据库读取的分类排名
        )
        for p, subscriber_count, global_rank, category_rank in rows
    ]


@router.get("/{podcast_id}", response_model=PodcastResponse)
async def get_podcast(
    podcast_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """获取单个播客详情（默认显示昨天的数据）"""
    from datetime import timedelta
    
    result = await session.execute(
        select(Podcast).where(Podcast.id == podcast_id)
    )
    podcast = result.scalar_one_or_none()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    # 默认使用昨天的日期
    target_date = date.today() - timedelta(days=1)
    
    # 获取目标日期及之前的最新指标（包含订阅数和排名）
    latest_metric_result = await session.execute(
        select(PodcastDailyMetric)
        .where(
            PodcastDailyMetric.podcast_id == podcast_id,
            PodcastDailyMetric.snapshot_date <= target_date
        )
        .order_by(desc(PodcastDailyMetric.snapshot_date))
        .limit(1)
    )
    latest_metric = latest_metric_result.scalar_one_or_none()
    
    subscriber_count = latest_metric.subscriber_count if latest_metric else None
    global_rank = latest_metric.global_rank if latest_metric else None
    category_rank = latest_metric.category_rank if latest_metric else None
    
    # 获取所有历史趋势数据（包括到目标日期）
    trend_result = await session.execute(
        select(PodcastDailyMetric)
        .where(
            PodcastDailyMetric.podcast_id == podcast_id,
            PodcastDailyMetric.snapshot_date <= target_date
        )
        .order_by(PodcastDailyMetric.snapshot_date)
    )
    trend_data = [
        TrendData(date=str(m.snapshot_date), subscriber_count=m.subscriber_count)
        for m in trend_result.scalars().all()
    ]
    
    return PodcastResponse(
        id=podcast.id,
        xyz_id=podcast.xyz_id,
        name=podcast.name,
        rss_url=podcast.rss_url,
        cover_url=podcast.cover_url,
        category=podcast.category,
        description=podcast.description,
        created_at=str(podcast.created_at) if podcast.created_at else '',
        updated_at=str(podcast.updated_at) if podcast.updated_at else '',
        subscriber_count=subscriber_count,
        trend=trend_data,
        rank=global_rank,  # 从数据库读取的全站排名
        category_rank=category_rank,  # 从数据库读取的分类排名
    )


@router.post("/", response_model=PodcastResponse, status_code=201)
async def create_podcast(
    data: PodcastCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """创建新播客"""
    # 检查 xyz_id 是否已存在
    result = await session.execute(
        select(Podcast).where(Podcast.xyz_id == data.xyz_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Podcast with this xyz_id already exists")
    
    podcast = Podcast(**data.model_dump())
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)
    return podcast


@router.patch("/{podcast_id}", response_model=PodcastResponse)
async def update_podcast(
    podcast_id: int,
    data: PodcastUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """更新播客信息"""
    result = await session.execute(
        select(Podcast).where(Podcast.id == podcast_id)
    )
    podcast = result.scalar_one_or_none()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(podcast, key, value)
    
    await session.commit()
    await session.refresh(podcast)
    return podcast


@router.delete("/{podcast_id}", status_code=204)
async def delete_podcast(
    podcast_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """删除播客"""
    result = await session.execute(
        select(Podcast).where(Podcast.id == podcast_id)
    )
    podcast = result.scalar_one_or_none()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    await session.delete(podcast)
    await session.commit()
    return None


@router.get("/{podcast_id}/metrics", response_model=List[DailyMetricResponse])
async def get_podcast_metrics(
    podcast_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """获取播客的每日指标"""
    # 验证播客存在
    result = await session.execute(
        select(Podcast).where(Podcast.id == podcast_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    query = select(PodcastDailyMetric).where(
        PodcastDailyMetric.podcast_id == podcast_id
    )
    if start_date:
        query = query.where(PodcastDailyMetric.snapshot_date >= start_date)
    if end_date:
        query = query.where(PodcastDailyMetric.snapshot_date <= end_date)
    
    query = query.order_by(desc(PodcastDailyMetric.snapshot_date))
    result = await session.execute(query)
    metrics = result.scalars().all()
    
    # 转换为响应格式
    return [
        DailyMetricResponse(
            id=m.id,
            podcast_id=m.podcast_id,
            snapshot_date=str(m.snapshot_date) if m.snapshot_date else '',
            subscriber_count=m.subscriber_count,
            created_at=str(m.created_at) if m.created_at else '',
        )
        for m in metrics
    ]


@router.post("/{podcast_id}/metrics", response_model=DailyMetricResponse, status_code=201)
async def create_podcast_metric(
    podcast_id: int,
    data: DailyMetricCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """创建播客的每日指标"""
    # 验证播客存在
    result = await session.execute(
        select(Podcast).where(Podcast.id == podcast_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    # 检查该日期是否已有记录
    result = await session.execute(
        select(PodcastDailyMetric).where(
            PodcastDailyMetric.podcast_id == podcast_id,
            PodcastDailyMetric.snapshot_date == data.snapshot_date
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Metric for this date already exists")
    
    metric = PodcastDailyMetric(
        podcast_id=podcast_id,
        **data.model_dump()
    )
    session.add(metric)
    await session.commit()
    await session.refresh(metric)
    return metric


class SubmitPodcastRequest(BaseModel):
    """提交播客链接请求"""
    url: str


@router.post("/submit", response_model=PodcastResponse)
async def submit_podcast(
    request: SubmitPodcastRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    提交播客链接
    
    如果播客已存在，直接返回
    如果不存在，创建新记录并返回
    """
    import re
    
    url = request.url.strip()
    
    # 解析URL，提取xyz_id
    # 支持的格式：
    # - https://www.xiaoyuzhoufm.com/podcast/{xyz_id}
    # - https://www.xiaoyuzhoufm.com/podcast/{xyz_id}?...
    xyz_id = None
    
    # 尝试从URL中提取ID
    patterns = [
        r'xiaoyuzhoufm\.com/podcast/([a-zA-Z0-9]+)',
        r'xiaoyuzhou\.fm/podcast/([a-zA-Z0-9]+)',
        r'/podcast/([a-zA-Z0-9]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            xyz_id = match.group(1)
            break
    
    if not xyz_id:
        raise HTTPException(
            status_code=400,
            detail="无法从URL中提取播客ID，请确保URL格式正确（例如：https://www.xiaoyuzhoufm.com/podcast/xxx）"
        )
    
    # 检查播客是否已存在
    existing_result = await session.execute(
        select(Podcast).where(Podcast.xyz_id == xyz_id)
    )
    existing_podcast = existing_result.scalar_one_or_none()
    
    if existing_podcast:
        # 播客已存在，返回现有记录
        # 获取最新订阅数和趋势数据
        latest_metric_result = await session.execute(
            select(PodcastDailyMetric)
            .where(PodcastDailyMetric.podcast_id == existing_podcast.id)
            .order_by(desc(PodcastDailyMetric.snapshot_date))
            .limit(1)
        )
        latest_metric = latest_metric_result.scalar_one_or_none()
        subscriber_count = latest_metric.subscriber_count if latest_metric else None
        
        trend_result = await session.execute(
            select(PodcastDailyMetric)
            .where(PodcastDailyMetric.podcast_id == existing_podcast.id)
            .order_by(PodcastDailyMetric.snapshot_date)
        )
        trend_data = [
            {'date': str(m.snapshot_date), 'subscriber_count': m.subscriber_count}
            for m in trend_result.scalars().all()
        ]
        
        # 计算排名（简化版，实际应该从list_podcasts的逻辑中复用）
        return PodcastResponse(
            id=existing_podcast.id,
            xyz_id=existing_podcast.xyz_id,
            name=existing_podcast.name,
            rss_url=existing_podcast.rss_url,
            cover_url=existing_podcast.cover_url,
            category=existing_podcast.category,
            description=existing_podcast.description,
            created_at=str(existing_podcast.created_at),
            updated_at=str(existing_podcast.updated_at),
            subscriber_count=subscriber_count,
            trend=trend_data,
            rank=None,  # 排名需要从列表查询中获取
            category_rank=None,
        )
    
    # 播客不存在，创建新记录
    # 先尝试从URL抓取基本信息（可选）
    new_podcast = Podcast(
        xyz_id=xyz_id,
        name=f"待抓取 - {xyz_id}",  # 临时名称，后续抓取时会更新
        rss_url=None,
        cover_url=None,
        category=None,
        description=None,
    )
    
    session.add(new_podcast)
    await session.commit()
    await session.refresh(new_podcast)
    
    return PodcastResponse(
        id=new_podcast.id,
        xyz_id=new_podcast.xyz_id,
        name=new_podcast.name,
        rss_url=new_podcast.rss_url,
        cover_url=new_podcast.cover_url,
        category=new_podcast.category,
        description=new_podcast.description,
        created_at=str(new_podcast.created_at),
        updated_at=str(new_podcast.updated_at),
        subscriber_count=None,
        trend=[],
        rank=None,
        category_rank=None,
    )


