#!/bin/bash
# 启动和测试脚本

echo "=========================================="
echo "XYZRank 项目测试"
echo "=========================================="

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  建议在虚拟环境中运行"
    echo "创建虚拟环境: python -m venv venv"
    echo "激活虚拟环境: source venv/bin/activate"
    echo ""
fi

# 检查依赖
echo "检查依赖..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 安装依赖..."
    pip install -r requirements.txt
else
    echo "✅ 依赖已安装"
fi
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置数据库信息"
    echo ""
fi

# 提示数据库配置
echo "=========================================="
echo "数据库配置检查："
echo "=========================================="
echo "请确保："
echo "1. MySQL 服务已启动"
echo "2. .env 文件中的数据库配置正确"
echo "3. 数据库已创建: CREATE DATABASE xyzrank;"
echo ""

read -p "数据库已配置好？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "请先配置数据库，然后重新运行此脚本"
    exit 1
fi

# 运行数据库迁移
echo ""
echo "🔄 运行数据库迁移..."
if [ ! -d "migrations/versions" ] || [ -z "$(ls -A migrations/versions 2>/dev/null)" ]; then
    echo "生成初始迁移..."
    alembic revision --autogenerate -m "Initial migration"
fi
alembic upgrade head
echo "✅ 数据库迁移完成"
echo ""

# 启动服务
echo "=========================================="
echo "启动服务..."
echo "=========================================="
echo "服务将在 http://localhost:8000 启动"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

