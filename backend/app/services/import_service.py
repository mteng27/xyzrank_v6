"""数据导入服务 - 从 Excel 文件导入播客数据"""
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.podcast import Podcast
from loguru import logger


async def import_podcasts_from_excel(
    file_path: str,
    session: AsyncSession,
    skip_existing: bool = True,
) -> dict:
    """
    从 Excel 文件导入播客数据
    
    Args:
        file_path: Excel 文件路径
        session: 数据库会话
        skip_existing: 是否跳过已存在的播客（基于 xyz_id）
    
    Returns:
        导入结果统计
    """
    try:
        df = pd.read_excel(file_path)
        logger.info(f"读取 Excel 文件: {file_path}, 共 {len(df)} 行数据")
        
        # 预期的列名映射（根据实际 Excel 文件调整）
        # Excel列名: ['get_time', 'album_id', 'album_name', 'category', 'summary', 'author_name', 'subscribe_count', 'link_url', 'track_count', 'create_time', 'update_time']
        column_mapping = {
            "xyz_id": ["xyz_id", "album_id", "小宇宙ID", "ID"],
            "name": ["name", "album_name", "名称", "播客名称", "title"],
            "rss_url": ["rss_url", "RSS", "rss"],
            "cover_url": ["cover_url", "封面", "封面图", "cover"],
            "category": ["category", "分类", "类别"],
            "description": ["description", "summary", "描述", "简介", "desc"],
        }
        
        # 找到实际列名
        actual_columns = {}
        for key, possible_names in column_mapping.items():
            for name in possible_names:
                if name in df.columns:
                    actual_columns[key] = name
                    break
        
        if "xyz_id" not in actual_columns or "name" not in actual_columns:
            raise ValueError(f"Excel 文件必须包含 xyz_id/album_id 和 name/album_name 列。当前列名: {df.columns.tolist()}")
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                xyz_id = str(row[actual_columns["xyz_id"]]).strip()
                name = str(row[actual_columns["name"]]).strip()
                
                if not xyz_id or not name:
                    error_count += 1
                    errors.append(f"第 {idx + 2} 行: xyz_id 或 name 为空")
                    continue
                
                # 检查是否已存在
                result = await session.execute(
                    select(Podcast).where(Podcast.xyz_id == xyz_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    if skip_existing:
                        skipped_count += 1
                        continue
                    else:
                        # 更新现有记录
                        for key, col_name in actual_columns.items():
                            if key != "xyz_id" and col_name in row:
                                value = row[col_name]
                                if pd.notna(value):
                                    setattr(existing, key, str(value).strip())
                        await session.commit()
                        created_count += 1
                        continue
                
                # 创建新记录
                podcast_data = {
                    "xyz_id": xyz_id,
                    "name": name,
                }
                
                # 处理各个字段
                for key, col_name in actual_columns.items():
                    if key not in ["xyz_id", "name"] and col_name in row:
                        value = row[col_name]
                        if pd.notna(value):
                            podcast_data[key] = str(value).strip()
                
                # 处理 link_url：如果有 link_url，可以尝试从中提取信息
                # 或者保存为 rss_url（如果 rss_url 为空）
                if "link_url" in df.columns and pd.notna(row.get("link_url")):
                    link_url = str(row["link_url"]).strip()
                    # 如果 rss_url 为空，可以尝试从 link_url 构建 RSS URL
                    # 或者保存 link_url 的某些信息
                    # 注意：Podcast 模型中没有 link_url 字段，只有 rss_url
                    # 如果 link_url 是播客页面链接，我们可以保留它作为参考
                    # 但这里我们先不处理，因为模型中没有这个字段
                
                podcast = Podcast(**podcast_data)
                session.add(podcast)
                created_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"第 {idx + 2} 行: {str(e)}")
                logger.error(f"导入第 {idx + 2} 行时出错: {e}")
        
        await session.commit()
        
        result = {
            "total": len(df),
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors[:10],  # 只返回前10个错误
        }
        
        logger.info(f"导入完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"导入 Excel 文件时出错: {e}")
        await session.rollback()
        raise


