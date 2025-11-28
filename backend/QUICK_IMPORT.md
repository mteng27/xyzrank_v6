# 快速导入指南

## 步骤1: 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 步骤2: 配置数据库

确保 `.env` 文件中的数据库配置正确：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DB=xyzrank
```

## 步骤3: 创建数据库并运行迁移

```bash
# 在MySQL中创建数据库
mysql -u root -p
CREATE DATABASE xyzrank CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 运行迁移
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 步骤4: 导入数据

### 方式A: 直接数据库导入（推荐）

```bash
# 测试导入100条（推荐先测试）
python import_to_db.py 100

# 导入全部数据
python import_to_db.py
```

### 方式B: 通过API导入

```bash
# 1. 启动服务
uvicorn app.main:app --reload

# 2. 在另一个终端运行
python import_data_simple.py
```

## 数据文件

- 支持格式: `.xlsx` 或 `.csv`
- 文件位置: 项目根目录 `小宇宙专辑资料-all.xlsx` 或 `小宇宙专辑资料-all.csv`

## 字段映射

Excel/CSV列名 -> 数据库字段：
- `album_id` -> `xyz_id` (小宇宙ID)
- `album_name` -> `name` (播客名称)
- `category` -> `category` (分类)
- `summary` -> `description` (描述)
- `link_url` -> (暂不导入，可用于后续抓取)

## 注意事项

1. 导入会跳过已存在的播客（基于 xyz_id）
2. 大量数据导入需要时间，建议先测试少量数据
3. 确保数据库连接正常

