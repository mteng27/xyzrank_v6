from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    xyz_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rss_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    daily_metrics: Mapped[list["PodcastDailyMetric"]] = relationship(
        back_populates="podcast", cascade="all, delete-orphan"
    )


class PodcastDailyMetric(Base):
    __tablename__ = "podcast_daily_metrics"
    __table_args__ = (
        UniqueConstraint("podcast_id", "snapshot_date", name="uq_podcast_snapshot"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    podcast_id: Mapped[int] = mapped_column(
        ForeignKey("podcasts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[str] = mapped_column(Date, nullable=False)
    subscriber_count: Mapped[int] = mapped_column(Integer, nullable=False)
    global_rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # 全站排名
    category_rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # 分类排名
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    podcast: Mapped[Podcast] = relationship(back_populates="daily_metrics")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")  # running, completed, failed
    total_podcasts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    successful_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
