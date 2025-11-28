#!/bin/bash
# 项目更新脚本
# 用于快速更新服务器上的代码

set -e

PROJECT_DIR="/opt/xyzrank"
BACKEND_DIR="$PROJECT_DIR/backend"

echo "=========================================="
echo "XYZRank 项目更新"
echo "=========================================="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 root 用户运行此脚本"
    exit 1
fi

cd "$PROJECT_DIR"

# 备份数据库
echo "[1/5] 备份数据库..."
if [ -f "$BACKEND_DIR/xyzrank.db" ]; then
    mkdir -p "$PROJECT_DIR/backup"
    cp "$BACKEND_DIR/xyzrank.db" "$PROJECT_DIR/backup/xyzrank_$(date +%Y%m%d_%H%M%S).db"
    echo "✓ 数据库备份完成"
fi
echo ""

# 更新代码（如果使用 Git）
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "[2/5] 从 Git 拉取最新代码..."
    git pull
    echo "✓ 代码更新完成"
else
    echo "[2/5] 未检测到 Git，请手动更新代码"
    echo "可以使用 rsync 从本地同步："
    echo "  rsync -avz --exclude '*.pyc' --exclude '__pycache__' \\"
    echo "    /Users/mateng/xyzrank_v6/ root@server:$PROJECT_DIR/"
fi
echo ""

# 更新依赖
echo "[3/5] 更新 Python 依赖..."
cd "$BACKEND_DIR"
source venv/bin/activate
pip install -r requirements.txt --upgrade
echo "✓ 依赖更新完成"
echo ""

# 运行数据库迁移
echo "[4/5] 运行数据库迁移..."
alembic upgrade head
echo "✓ 数据库迁移完成"
echo ""

# 重启服务
echo "[5/5] 重启服务..."
systemctl restart xyzrank-backend
sleep 2
systemctl status xyzrank-backend --no-pager | head -10
echo ""

echo "=========================================="
echo "✅ 更新完成！"
echo "=========================================="

