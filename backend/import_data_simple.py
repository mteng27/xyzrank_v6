"""简化的数据导入脚本 - 不依赖数据库连接，直接使用API"""
import requests
import pandas as pd
from pathlib import Path
import json
import sys

BASE_URL = "http://localhost:8000"


def import_via_api(file_path: str, base_url: str = BASE_URL):
    """通过API导入数据"""
    print("=" * 60)
    print("通过API导入播客数据")
    print("=" * 60)
    print()
    
    # 读取文件（支持Excel和CSV）
    print(f"📖 读取文件: {file_path}")
    file_ext = Path(file_path).suffix.lower()
    if file_ext == '.csv':
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    print(f"总记录数: {len(df)}")
    print()
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 服务未正常运行 (状态码: {response.status_code})")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务: {e}")
        print(f"请确保服务已启动: uvicorn app.main:app --reload")
        return
    
    print("✅ 服务连接正常")
    print()
    
    # 准备数据
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    print("🚀 开始导入数据...")
    print()
    
    # 批量导入（每次100条）
    batch_size = 100
    total_batches = (len(df) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(df))
        batch_df = df.iloc[start_idx:end_idx]
        
        print(f"处理批次 {batch_num + 1}/{total_batches} (行 {start_idx + 1}-{end_idx})...")
        
        for idx, row in batch_df.iterrows():
            try:
                # 准备数据
                album_id = str(row.get('album_id', '')).strip()
                album_name = str(row.get('album_name', '')).strip()
                
                if not album_id or not album_name or album_id == 'nan' or album_name == 'nan':
                    error_count += 1
                    errors.append(f"第 {idx + 2} 行: album_id 或 album_name 为空")
                    continue
                
                # 构建请求数据
                podcast_data = {
                    "xyz_id": album_id,
                    "name": album_name,
                }
                
                # 添加可选字段
                if pd.notna(row.get('category')):
                    podcast_data["category"] = str(row['category']).strip()
                
                if pd.notna(row.get('summary')):
                    podcast_data["description"] = str(row['summary']).strip()
                
                # 发送请求
                response = requests.post(
                    f"{base_url}/api/podcasts/",
                    json=podcast_data,
                    timeout=10
                )
                
                if response.status_code == 201:
                    created_count += 1
                elif response.status_code == 400 and "already exists" in response.text:
                    skipped_count += 1
                else:
                    error_count += 1
                    error_msg = f"第 {idx + 2} 行: HTTP {response.status_code}"
                    try:
                        error_detail = response.json().get('detail', '')
                        error_msg += f" - {error_detail}"
                    except:
                        pass
                    errors.append(error_msg)
                    if error_count <= 5:  # 只打印前5个错误
                        print(f"  ⚠️  {error_msg}")
                
            except Exception as e:
                error_count += 1
                error_msg = f"第 {idx + 2} 行: {str(e)}"
                errors.append(error_msg)
                if error_count <= 5:
                    print(f"  ❌ {error_msg}")
        
        # 显示进度
        processed = end_idx
        print(f"  已处理: {processed}/{len(df)} ({processed/len(df)*100:.1f}%)")
        print()
    
    # 显示结果
    print("=" * 60)
    print("导入完成！")
    print("=" * 60)
    print(f"总记录数: {len(df)}")
    print(f"✅ 成功创建: {created_count}")
    print(f"⏭️  跳过（已存在）: {skipped_count}")
    print(f"❌ 错误数: {error_count}")
    
    if errors and error_count <= 20:
        print()
        print("错误详情:")
        for error in errors[:20]:
            print(f"  - {error}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    # 尝试多个可能的路径
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    possible_paths = [
        project_root / "小宇宙专辑资料-all.xlsx",
        project_root / "小宇宙专辑资料-all.csv",
        Path("/Users/mateng/xyzrank_v6/小宇宙专辑资料-all.xlsx"),
        Path("/Users/mateng/xyzrank_v6/小宇宙专辑资料-all.csv"),
        Path("小宇宙专辑资料-all.xlsx"),
        Path("小宇宙专辑资料-all.csv"),
    ]
    
    excel_path = None
    for path in possible_paths:
        try:
            if path.exists():
                excel_path = path
                break
        except:
            continue
    
    if not excel_path:
        print("❌ Excel文件不存在，尝试的路径:")
        for path in possible_paths:
            print(f"  - {path}")
        print(f"\n当前工作目录: {Path.cwd()}")
        print("请确保Excel文件在项目根目录或指定正确路径")
        print("\n或者手动指定路径:")
        print("  python import_data_simple.py /path/to/小宇宙专辑资料-all.xlsx")
        sys.exit(1)
    
    print(f"📁 使用Excel文件: {excel_path}")
    print()
    import_via_api(str(excel_path))

