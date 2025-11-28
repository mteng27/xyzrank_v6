"""完整导入两个数据表格到数据库"""
import asyncio
import sys
import pandas as pd
from pathlib import Path
import sqlite3
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def setup_database():
    """设置数据库表"""
    print("=" * 60)
    print("设置数据库")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent / "xyzrank.db"
    
    # 创建数据库连接
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("📝 创建数据表...")
    
    # Podcasts表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS podcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            xyz_id VARCHAR(64) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            rss_url VARCHAR(512),
            cover_url VARCHAR(512),
            category VARCHAR(128),
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # PodcastDailyMetric表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS podcast_daily_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER NOT NULL,
            snapshot_date DATE NOT NULL,
            subscriber_count INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES podcasts(id) ON DELETE CASCADE,
            UNIQUE(podcast_id, snapshot_date)
        )
    """)
    
    # ScrapeRun表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            status VARCHAR(32) DEFAULT 'running',
            total_podcasts INTEGER,
            successful_count INTEGER,
            failed_count INTEGER,
            error_message TEXT
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_podcasts_xyz_id ON podcasts(xyz_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_podcast_id ON podcast_daily_metrics(podcast_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_date ON podcast_daily_metrics(snapshot_date)")
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库表已创建: {db_path}")
    print()
    return str(db_path)


def import_podcasts(file_path: str):
    """导入播客基本信息"""
    print("=" * 60)
    print("步骤 1: 导入播客基本信息（全量专辑）")
    print("=" * 60)
    print()
    
    print(f"📖 读取文件: {file_path}")
    df = pd.read_csv(file_path)
    print(f"总记录数: {len(df)}")
    print()
    
    # 更严格地过滤：排除NaN、空字符串和'nan'字符串
    def is_valid_id(val):
        if pd.isna(val):
            return False
        val_str = str(val).strip()
        return val_str and val_str.lower() != 'nan' and val_str != ''
    
    def is_valid_name(val):
        if pd.isna(val):
            return False
        val_str = str(val).strip()
        return val_str and val_str.lower() != 'nan' and val_str != ''
    
    df_valid = df[
        df['album_id'].apply(is_valid_id) & 
        df['album_name'].apply(is_valid_name)
    ].copy()
    print(f"有效记录数: {len(df_valid)} (过滤了 {len(df) - len(df_valid)} 条无效数据)")
    print()
    
    db_path = Path(__file__).parent / "xyzrank.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    print("🚀 开始导入播客数据...")
    print()
    
    batch_size = 100
    total = len(df_valid)
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_df = df_valid.iloc[batch_start:batch_end]
        
        print(f"处理批次: {batch_start + 1}-{batch_end}/{total} ({batch_end/total*100:.1f}%)...")
        
        for idx, row in batch_df.iterrows():
            try:
                album_id = str(row['album_id']).strip()
                album_name = str(row['album_name']).strip()
                
                if not album_id or not album_name:
                    error_count += 1
                    continue
                
                # 检查是否已存在
                cursor.execute("SELECT id FROM podcasts WHERE xyz_id = ?", (album_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有记录
                    category = str(row['category']).strip() if pd.notna(row.get('category')) else None
                    description = str(row['summary']).strip() if pd.notna(row.get('summary')) else None
                    
                    cursor.execute("""
                        UPDATE podcasts 
                        SET name = ?, category = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE xyz_id = ?
                    """, (album_name, category, description, album_id))
                    updated_count += 1
                else:
                    # 创建新记录
                    category = str(row['category']).strip() if pd.notna(row.get('category')) else None
                    description = str(row['summary']).strip() if pd.notna(row.get('summary')) else None
                    
                    cursor.execute("""
                        INSERT INTO podcasts (xyz_id, name, category, description)
                        VALUES (?, ?, ?, ?)
                    """, (album_id, album_name, category, description))
                    created_count += 1
                
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    errors.append(f"第 {idx + 2} 行: {str(e)}")
        
        conn.commit()
        print(f"  ✅ 已提交批次")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("播客数据导入完成！")
    print("=" * 60)
    print(f"总记录数: {total}")
    print(f"✅ 成功创建: {created_count}")
    print(f"🔄 更新: {updated_count}")
    print(f"❌ 错误数: {error_count}")
    print()
    
    return created_count + updated_count


def import_subscriber_metrics(file_path: str):
    """导入订阅量历史数据"""
    print("=" * 60)
    print("步骤 2: 导入订阅量历史数据（部分订阅量）")
    print("=" * 60)
    print()
    
    print(f"📖 读取文件: {file_path}")
    df = pd.read_csv(file_path)
    print(f"总记录数: {len(df)}")
    print()
    
    # 过滤有效数据
    df_valid = df[
        df['album_id'].notna() & 
        df['subscribe_count'].notna() & 
        df['update_time'].notna()
    ].copy()
    print(f"有效记录数: {len(df_valid)} (过滤了 {len(df) - len(df_valid)} 条无效数据)")
    print()
    
    db_path = Path(__file__).parent / "xyzrank.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 创建album_id到podcast_id的映射
    print("📋 创建播客ID映射...")
    cursor.execute("SELECT id, xyz_id FROM podcasts")
    id_mapping = {xyz_id: pid for pid, xyz_id in cursor.fetchall()}
    print(f"✅ 找到 {len(id_mapping)} 个播客")
    print()
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    print("🚀 开始导入订阅量数据...")
    print()
    
    batch_size = 500
    total = len(df_valid)
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_df = df_valid.iloc[batch_start:batch_end]
        
        print(f"处理批次: {batch_start + 1}-{batch_end}/{total} ({batch_end/total*100:.1f}%)...")
        
        for idx, row in batch_df.iterrows():
            try:
                album_id = str(row['album_id']).strip()
                
                # 查找对应的podcast_id
                podcast_id = id_mapping.get(album_id)
                if not podcast_id:
                    skipped_count += 1
                    continue
                
                # 解析订阅数量
                try:
                    subscriber_count = int(float(row['subscribe_count']))
                except (ValueError, TypeError):
                    error_count += 1
                    continue
                
                # 解析日期（从update_time提取日期部分）
                update_time = str(row['update_time']).strip()
                try:
                    # 尝试解析ISO格式时间
                    if 'T' in update_time:
                        dt = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S')
                    snapshot_date = dt.date().isoformat()
                except:
                    # 如果解析失败，尝试只提取日期部分
                    if 'T' in update_time:
                        snapshot_date = update_time.split('T')[0]
                    else:
                        snapshot_date = update_time[:10]
                
                # 插入或更新指标（使用INSERT OR REPLACE处理唯一约束）
                cursor.execute("""
                    INSERT OR REPLACE INTO podcast_daily_metrics 
                    (podcast_id, snapshot_date, subscriber_count)
                    VALUES (?, ?, ?)
                """, (podcast_id, snapshot_date, subscriber_count))
                
                imported_count += 1
                
            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    errors.append(f"第 {idx + 2} 行: {str(e)}")
        
        conn.commit()
        print(f"  ✅ 已提交批次 (已导入: {imported_count}, 跳过: {skipped_count})")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("订阅量数据导入完成！")
    print("=" * 60)
    print(f"总记录数: {total}")
    print(f"✅ 成功导入: {imported_count}")
    print(f"⏭️  跳过（无对应播客）: {skipped_count}")
    print(f"❌ 错误数: {error_count}")
    if errors:
        print()
        print("错误示例（前10个）:")
        for error in errors[:10]:
            print(f"  - {error}")
    print()
    
    return imported_count


def verify_import():
    """验证导入结果"""
    print("=" * 60)
    print("验证导入结果")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent / "xyzrank.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 统计播客
    cursor.execute("SELECT COUNT(*) FROM podcasts")
    podcast_count = cursor.fetchone()[0]
    
    # 统计指标
    cursor.execute("SELECT COUNT(*) FROM podcast_daily_metrics")
    metric_count = cursor.fetchone()[0]
    
    # 统计有指标的播客数
    cursor.execute("SELECT COUNT(DISTINCT podcast_id) FROM podcast_daily_metrics")
    podcasts_with_metrics = cursor.fetchone()[0]
    
    # 分类统计
    cursor.execute("""
        SELECT category, COUNT(*) as cnt 
        FROM podcasts 
        WHERE category IS NOT NULL
        GROUP BY category 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    categories = cursor.fetchall()
    
    # 指标日期范围
    cursor.execute("""
        SELECT MIN(snapshot_date), MAX(snapshot_date), COUNT(DISTINCT snapshot_date)
        FROM podcast_daily_metrics
    """)
    date_range = cursor.fetchone()
    
    print(f"📊 数据统计:")
    print(f"  播客总数: {podcast_count}")
    print(f"  订阅量记录数: {metric_count}")
    print(f"  有历史数据的播客数: {podcasts_with_metrics}")
    if date_range[0]:
        print(f"  日期范围: {date_range[0]} 至 {date_range[1]}")
        print(f"  不同日期数: {date_range[2]}")
    print()
    
    print("📈 分类统计（前10）:")
    for cat, cnt in categories:
        print(f"  {cat}: {cnt}")
    print()
    
    conn.close()


async def main():
    """主函数"""
    print()
    print("=" * 60)
    print("XYZRank 完整数据导入工具")
    print("=" * 60)
    print()
    
    # 设置数据库
    db_path = setup_database()
    
    # 查找文件
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    podcasts_file = project_root / "小宇宙全量专辑.csv"
    metrics_file = project_root / "小宇宙播客部分订阅量.csv"
    
    if not podcasts_file.exists():
        print(f"❌ 播客数据文件不存在: {podcasts_file}")
        return
    
    if not metrics_file.exists():
        print(f"❌ 订阅量数据文件不存在: {metrics_file}")
        return
    
    # 导入播客数据
    podcast_count = import_podcasts(str(podcasts_file))
    
    # 导入订阅量数据
    metric_count = import_subscriber_metrics(str(metrics_file))
    
    # 验证导入
    verify_import()
    
    print("=" * 60)
    print("✅ 所有数据导入完成！")
    print("=" * 60)
    print(f"数据库位置: {db_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

