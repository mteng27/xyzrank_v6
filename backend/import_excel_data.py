"""从Excel文件导入播客数据到数据库"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionFactory
from app.services.import_service import import_podcasts_from_excel


async def main():
    """主函数"""
    print("=" * 60)
    print("播客数据导入工具")
    print("=" * 60)
    print()
    
    # Excel文件路径
    excel_path = Path(__file__).parent.parent / "小宇宙专辑资料-all.xlsx"
    
    if not excel_path.exists():
        print(f"❌ Excel文件不存在: {excel_path}")
        print("请确保文件路径正确")
        return
    
    print(f"📖 读取Excel文件: {excel_path}")
    print()
    
    # 创建数据库会话
    async with AsyncSessionFactory() as session:
        try:
            # 执行导入
            print("🚀 开始导入数据...")
            print("提示: 如果播客已存在，将跳过（skip_existing=True）")
            print()
            
            result = await import_podcasts_from_excel(
                str(excel_path),
                session,
                skip_existing=True  # 跳过已存在的播客
            )
            
            print("=" * 60)
            print("导入完成！")
            print("=" * 60)
            print(f"总记录数: {result['total']}")
            print(f"✅ 成功创建: {result['created']}")
            print(f"⏭️  跳过（已存在）: {result['skipped']}")
            print(f"❌ 错误数: {result['errors']}")
            
            if result['errors'] > 0:
                print()
                print("错误详情（前10个）:")
                for error in result.get('error_details', []):
                    print(f"  - {error}")
            
            print()
            print("=" * 60)
            print("✅ 导入完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 导入失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(main())

