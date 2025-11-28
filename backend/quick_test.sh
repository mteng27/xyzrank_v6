#!/bin/bash
# 快速测试脚本

set -e

echo "=========================================="
echo "XYZRank 项目本地测试脚本"
echo "=========================================="
echo ""

# 检查 Python
echo "1. 检查 Python 环境..."
python --version
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "2. 创建虚拟环境..."
    python -m venv venv
    echo "虚拟环境已创建"
else
    echo "2. 虚拟环境已存在"
fi
echo ""

# 激活虚拟环境并安装依赖
echo "3. 安装依赖..."
source venv/bin/activate
pip install -q -r requirements.txt
echo "依赖安装完成"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "4. 创建 .env 文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件配置数据库信息"
    echo ""
fi

# 检查数据库连接
echo "5. 检查数据库配置..."
if grep -q "MYSQL_PASSWORD=xyzrank" .env; then
    echo "⚠️  请修改 .env 文件中的数据库密码"
fi
echo ""

echo "=========================================="
echo "下一步操作："
echo "1. 编辑 .env 文件配置数据库"
echo "2. 创建数据库: CREATE DATABASE xyzrank;"
echo "3. 运行迁移: alembic revision --autogenerate -m 'Initial' && alembic upgrade head"
echo "4. 启动服务: uvicorn app.main:app --reload"
echo "5. 运行测试: python test_api.py"
echo "=========================================="

