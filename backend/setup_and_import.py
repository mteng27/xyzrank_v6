"""自动配置数据库并导入数据"""
import asyncio
import sys
import subprocess
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def check_and_install_dependencies():
    """检查并安装依赖"""
    print("=" * 60)
    print("步骤 1: 检查依赖")
    print("=" * 60)
    print()
    
    try:
        import fastapi
        import sqlalchemy
        import pandas
        print("✅ 核心依赖已安装")
        return True
    except ImportError:
        print("⚠️  检测到缺少依赖，正在安装...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-q", 
                "-r", "requirements.txt"
            ])
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            return False


def check_mysql_connection():
    """检查MySQL连接"""
    print()
    print("=" * 60)
    print("步骤 2: 检查数据库连接")
    print("=" * 60)
    print()
    
    try:
        from app.core.config import settings
        print(f"数据库配置:")
        print(f"  Host: {settings.mysql_host}")
        print(f"  Port: {settings.mysql_port}")
        print(f"  User: {settings.mysql_user}")
        print(f"  Database: {settings.mysql_db}")
        print()
        
        # 尝试连接（使用同步连接测试）
        try:
            import pymysql
            conn = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                charset='utf8mb4'
            )
            print("✅ MySQL连接成功")
            conn.close()
            return True
        except ImportError:
            print("⚠️  pymysql未安装，跳过连接测试")
            return True
        except Exception as e:
            print(f"⚠️  连接测试失败: {e}")
            print("提示: 请确保MySQL服务已启动，并且用户有足够权限")
            return False
            
    except Exception as e:
        print(f"❌ 配置读取失败: {e}")
        return False


def create_database():
    """创建数据库"""
    print()
    print("=" * 60)
    print("步骤 3: 创建数据库")
    print("=" * 60)
    print()
    
    try:
        from app.core.config import settings
        import pymysql
        
        try:
            conn = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                charset='utf8mb4'
            )
            cursor = conn.cursor()
            
            # 检查数据库是否存在
            cursor.execute(f"SHOW DATABASES LIKE '{settings.mysql_db}'")
            if cursor.fetchone():
                print(f"✅ 数据库 '{settings.mysql_db}' 已存在")
            else:
                # 创建数据库
                cursor.execute(
                    f"CREATE DATABASE {settings.mysql_db} "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                print(f"✅ 数据库 '{settings.mysql_db}' 创建成功")
            
            cursor.close()
            conn.close()
            return True
            
        except ImportError:
            print("⚠️  pymysql未安装，无法自动创建数据库")
            print(f"请手动创建数据库: CREATE DATABASE {settings.mysql_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            return True
        except Exception as e:
            print(f"⚠️  创建数据库失败: {e}")
            print("提示: 请手动创建数据库或检查权限")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def run_migrations():
    """运行数据库迁移"""
    print()
    print("=" * 60)
    print("步骤 4: 运行数据库迁移")
    print("=" * 60)
    print()
    
    try:
        # 检查是否有迁移文件
        migrations_dir = Path(__file__).parent / "migrations" / "versions"
        migration_files = list(migrations_dir.glob("*.py")) if migrations_dir.exists() else []
        
        if not migration_files:
            print("📝 生成初始迁移文件...")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "Initial migration"],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"⚠️  生成迁移文件时出现警告: {result.stderr}")
            else:
                print("✅ 迁移文件生成成功")
        
        print("🔄 执行数据库迁移...")
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ 数据库迁移完成")
            return True
        else:
            print(f"⚠️  迁移执行输出: {result.stdout}")
            if result.stderr:
                print(f"⚠️  迁移执行错误: {result.stderr}")
            # 即使有警告也继续
            return True
            
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False


async def import_data(limit=None):
    """导入数据"""
    print()
    print("=" * 60)
    print("步骤 5: 导入数据")
    print("=" * 60)
    print()
    
    try:
        # 导入导入脚本
        from import_to_db import import_podcasts_from_file
        
        # 查找文件
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        
        possible_paths = [
            project_root / "小宇宙专辑资料-all.xlsx",
            project_root / "小宇宙专辑资料-all.csv",
        ]
        
        file_path = None
        for path in possible_paths:
            if path.exists():
                file_path = path
                break
        
        if not file_path:
            print("❌ 数据文件不存在")
            return False
        
        print(f"📁 使用文件: {file_path}")
        if limit:
            print(f"⚠️  限制导入数量: {limit} (测试模式)")
        print()
        
        await import_podcasts_from_file(str(file_path), limit=limit)
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print()
    print("=" * 60)
    print("XYZRank 数据库配置和数据导入工具")
    print("=" * 60)
    print()
    
    # 检查命令行参数
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"⚠️  测试模式: 将只导入前 {limit} 条数据")
            print()
        except ValueError:
            print(f"⚠️  无效的数量参数: {sys.argv[1]}，将导入全部数据")
            print()
    
    # 步骤1: 检查依赖
    if not check_and_install_dependencies():
        print("\n❌ 依赖检查失败，请手动安装: pip install -r requirements.txt")
        return
    
    # 步骤2: 检查数据库连接
    if not check_mysql_connection():
        print("\n⚠️  数据库连接检查失败，但将继续尝试...")
    
    # 步骤3: 创建数据库
    if not create_database():
        print("\n⚠️  数据库创建失败，请手动创建数据库")
        response = input("是否继续？(y/n): ")
        if response.lower() != 'y':
            return
    
    # 步骤4: 运行迁移
    if not run_migrations():
        print("\n⚠️  迁移执行有问题，但将继续尝试导入...")
        response = input("是否继续？(y/n): ")
        if response.lower() != 'y':
            return
    
    # 步骤5: 导入数据
    success = await import_data(limit=limit)
    
    print()
    print("=" * 60)
    if success:
        print("✅ 配置和导入完成！")
    else:
        print("⚠️  导入过程中出现问题，请检查上面的错误信息")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


