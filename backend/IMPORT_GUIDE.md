# 数据导入指南

## 方式一：通过API导入（推荐）

如果服务已启动，可以使用API方式导入：

```bash
# 1. 确保服务已启动
uvicorn app.main:app --reload

# 2. 在另一个终端运行导入脚本
python import_data_simple.py
```

## 方式二：直接数据库导入

如果数据库已配置，可以直接导入：

```bash
# 1. 确保数据库已创建并迁移完成
alembic upgrade head

# 2. 运行导入脚本
python import_excel_data.py
```

## Excel文件字段映射

Excel列名 -> 数据库字段：
- `album_id` -> `xyz_id`
- `album_name` -> `name`
- `category` -> `category`
- `summary` -> `description`
- `link_url` -> (暂不导入，可用于后续抓取)

## 注意事项

1. 导入会跳过已存在的播客（基于 xyz_id）
2. 大量数据导入可能需要一些时间
3. 建议先测试少量数据

