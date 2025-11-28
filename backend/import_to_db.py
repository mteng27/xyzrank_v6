"""直接导入数据到数据库（不依赖API服务）"""
import asyncio
import sys
import pandas as pd
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionFactory
from app.models.podcast import Podcast


async def import_podcasts_from_file(file_path: str, limit: int = None):
    """从文件导入播客数据"""
    print("=" * 60)
    print("播客数据导入工具（直接数据库导入）")
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
    
    # 检查列名
    print("文件列名:", df.columns.tolist())
    print()
    
    # 字段映射
    column_mapping = {
        'xyz_id': 'album_id',
        'name': 'album_name',
        'category': 'category',
        'description': 'summary',
    }
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    print("🚀 开始导入数据...")
    print()
    
    async with AsyncSessionFactory() as session:
        try:
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
                        result = await session.execute(
                            select(Podcast).where(Podcast.xyz_id == album_id)
                        )
                        existing = result.scalar_one_or_none()
                        
                        if existing:
                            skipped_count += 1
                            continue
                        
                        # 创建新记录
                        podcast_data = {
                            "xyz_id": album_id,
                            "name": album_name,
                        }
                        
                        # 添加可选字段
                        if pd.notna(row.get('category')):
                            podcast_data["category"] = str(row['category']).strip()
                        
                        if pd.notna(row.get('summary')):
                            podcast_data["description"] = str(row['summary']).strip()
                        
                        podcast = Podcast(**podcast_data)
                        session.add(podcast)
                        created_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        error_msg = f"第 {idx + 2} 行: {str(e)}"
                        errors.append(error_msg)
                        if error_count <= 5:
                            print(f"  ❌ {error_msg}")
                
                # 提交批次
                await session.commit()
                print(f"  ✅ 已提交批次")
            
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
            
        except Exception as e:
            print(f"❌ 导入失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


async def main():
    """主函数"""
    # 查找文件
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    possible_paths = [
        project_root / "小宇宙专辑资料-all.xlsx",
        project_root / "小宇宙专辑资料-all.csv",
        Path("/Users/mateng/xyzrank_v6/小宇宙专辑资料-all.csv"),
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
    
    # 询问是否限制数量（测试用）
    import sys
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        print(f"⚠️  限制导入数量: {limit}")
    else:
        limit = None
        print("💡 提示: 可以指定导入数量进行测试，例如: python import_to_db.py 100")
    print()
    
    await import_podcasts_from_file(str(file_path), limit=limit)


if __name__ == "__main__":
    asyncio.run(main())

