"""使用SQLite的简化配置和导入脚本（无需MySQL）"""
import asyncio
import sys
import pandas as pd
from pathlib import Path
import sqlite3

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def setup_sqlite_database():
    """设置SQLite数据库"""
    print("=" * 60)
    print("使用 SQLite 数据库（无需MySQL）")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent / "xyzrank.db"
    
    # 创建数据库连接
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 创建表
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
    
    print(f"✅ 数据库已创建: {db_path}")
    print()
    return str(db_path)


async def import_to_sqlite(file_path: str, limit: int = None):
    """导入数据到SQLite"""
    print("=" * 60)
    print("导入数据到 SQLite")
    print("=" * 60)
    print()
    
    # 读取文件
    file_ext = Path(file_path).suffix.lower()
    print(f"📖 读取文件: {file_path}")
    
    if file_ext == '.csv':
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    if limit:
        df = df.head(limit)
        print(f"⚠️  限制导入数量: {limit}")
    
    print(f"总记录数: {len(df)}")
    print()
    
    # 连接数据库
    db_path = Path(__file__).parent / "xyzrank.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    print("🚀 开始导入数据...")
    print()
    
    # 批量处理
    batch_size = 100
    total = len(df)
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_df = df.iloc[batch_start:batch_end]
        
        print(f"处理批次: {batch_start + 1}-{batch_end}/{total} ({batch_end/total*100:.1f}%)...")
        
        for idx, row in batch_df.iterrows():
            try:
                # 提取数据
                album_id = str(row.get('album_id', '')).strip()
                album_name = str(row.get('album_name', '')).strip()
                
                if not album_id or not album_name or album_id == 'nan' or album_name == 'nan':
                    error_count += 1
                    errors.append(f"第 {idx + 2} 行: album_id 或 album_name 为空")
                    continue
                
                # 检查是否已存在
                cursor.execute("SELECT id FROM podcasts WHERE xyz_id = ?", (album_id,))
                if cursor.fetchone():
                    skipped_count += 1
                    continue
                
                # 准备数据
                category = None
                if pd.notna(row.get('category')):
                    category = str(row['category']).strip()
                
                description = None
                if pd.notna(row.get('summary')):
                    description = str(row['summary']).strip()
                
                # 插入数据
                cursor.execute("""
                    INSERT INTO podcasts (xyz_id, name, category, description)
                    VALUES (?, ?, ?, ?)
                """, (album_id, album_name, category, description))
                
                created_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = f"第 {idx + 2} 行: {str(e)}"
                errors.append(error_msg)
                if error_count <= 5:
                    print(f"  ❌ {error_msg}")
        
        # 提交批次
        conn.commit()
        print(f"  ✅ 已提交批次")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("导入完成！")
    print("=" * 60)
    print(f"总记录数: {total}")
    print(f"✅ 成功创建: {created_count}")
    print(f"⏭️  跳过（已存在）: {skipped_count}")
    print(f"❌ 错误数: {error_count}")
    
    if errors and error_count <= 20:
        print()
        print("错误详情（前20个）:")
        for error in errors[:20]:
            print(f"  - {error}")
    
    print()
    print("=" * 60)
    print(f"✅ 数据已导入到: {db_path}")
    print("=" * 60)


async def main():
    """主函数"""
    print()
    print("=" * 60)
    print("XYZRank 数据导入工具（SQLite版本）")
    print("=" * 60)
    print()
    
    # 检查命令行参数
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"⚠️  测试模式: 将只导入前 {limit} 条数据")
        except ValueError:
            print(f"⚠️  无效的数量参数: {sys.argv[1]}，将导入全部数据")
    print()
    
    # 设置数据库
    db_path = setup_sqlite_database()
    
    # 查找数据文件
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    possible_paths = [
        project_root / "小宇宙全量专辑.csv",
        project_root / "小宇宙专辑资料-all.xlsx",
        project_root / "小宇宙专辑资料-all.csv",
        Path("/Users/mateng/xyzrank_v6/小宇宙全量专辑.csv"),
        Path("/Users/mateng/xyzrank_v6/小宇宙专辑资料-all.csv"),
        Path("/Users/mateng/xyzrank_v6/小宇宙专辑资料-all.xlsx"),
        Path("小宇宙全量专辑.csv"),
        Path("小宇宙专辑资料-all.csv"),
        Path("小宇宙专辑资料-all.xlsx"),
    ]
    
    file_path = None
    for path in possible_paths:
        if path.exists():
            file_path = path
            break
    
    if not file_path:
        print("❌ 数据文件不存在")
        print("尝试的路径:")
        for path in possible_paths:
            print(f"  - {path}")
        return
    
    print(f"📁 使用文件: {file_path}")
    print()
    
    # 导入数据
    await import_to_sqlite(str(file_path), limit=limit)


if __name__ == "__main__":
    asyncio.run(main())

