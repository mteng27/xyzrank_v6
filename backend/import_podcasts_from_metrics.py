"""从订阅量文件中补充播客信息"""
import pandas as pd
import sqlite3
from pathlib import Path


def supplement_podcasts_from_metrics():
    """从订阅量文件中补充缺失的播客"""
    print("=" * 60)
    print("从订阅量文件补充播客信息")
    print("=" * 60)
    print()
    
    # 读取订阅量文件
    metrics_file = Path(__file__).parent.parent / "小宇宙播客部分订阅量.csv"
    print(f"📖 读取订阅量文件: {metrics_file}")
    df_metrics = pd.read_csv(metrics_file)
    print(f"总记录数: {len(df_metrics)}")
    print()
    
    # 获取所有唯一的播客信息（取每个播客的第一条记录）
    print("📋 提取唯一播客信息...")
    podcasts_from_metrics = df_metrics.groupby('album_id').first().reset_index()
    print(f"唯一播客数: {len(podcasts_from_metrics)}")
    print()
    
    # 连接数据库
    db_path = Path(__file__).parent / "xyzrank.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取数据库中已有的播客ID
    cursor.execute("SELECT xyz_id FROM podcasts")
    existing_ids = {row[0] for row in cursor.fetchall()}
    print(f"数据库中已有播客数: {len(existing_ids)}")
    print()
    
    # 找出需要补充的播客
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
    
    new_podcasts = podcasts_from_metrics[
        podcasts_from_metrics['album_id'].apply(is_valid_id) &
        podcasts_from_metrics['album_name'].apply(is_valid_name) &
        (~podcasts_from_metrics['album_id'].isin(existing_ids))
    ].copy()
    
    print(f"需要补充的播客数: {len(new_podcasts)}")
    print()
    
    if len(new_podcasts) == 0:
        print("✅ 没有需要补充的播客")
        conn.close()
        return 0
    
    # 导入新播客
    print("🚀 开始补充播客数据...")
    print()
    
    created_count = 0
    error_count = 0
    
    batch_size = 100
    total = len(new_podcasts)
    
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_df = new_podcasts.iloc[batch_start:batch_end]
        
        print(f"处理批次: {batch_start + 1}-{batch_end}/{total} ({batch_end/total*100:.1f}%)...")
        
        for idx, row in batch_df.iterrows():
            try:
                album_id = str(row['album_id']).strip()
                album_name = str(row['album_name']).strip()
                
                if not album_id or not album_name:
                    error_count += 1
                    continue
                
                # 提取其他字段
                category = None
                if pd.notna(row.get('category')):
                    cat_str = str(row['category']).strip()
                    if cat_str and cat_str.lower() != 'nan':
                        category = cat_str
                
                # 插入新播客
                cursor.execute("""
                    INSERT INTO podcasts (xyz_id, name, category, description)
                    VALUES (?, ?, ?, ?)
                """, (album_id, album_name, category, None))
                
                created_count += 1
                
            except sqlite3.IntegrityError:
                # 如果已存在（并发情况），跳过
                pass
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  ❌ 错误: {str(e)}")
        
        conn.commit()
        print(f"  ✅ 已提交批次")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("补充完成！")
    print("=" * 60)
    print(f"✅ 成功补充: {created_count}")
    print(f"❌ 错误数: {error_count}")
    print()
    
    return created_count


if __name__ == "__main__":
    supplement_podcasts_from_metrics()


