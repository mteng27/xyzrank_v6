#!/bin/bash
# 修复容器重启问题的脚本

set -e

echo "=========================================="
echo "修复 XYZRank 容器重启问题"
echo "=========================================="
echo ""

COMPOSE_FILE="docker-compose.cn.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

echo "使用配置文件: $COMPOSE_FILE"
echo ""

# 1. 停止所有容器
echo "[1/5] 停止所有容器..."
docker-compose -f $COMPOSE_FILE down
echo "✓ 容器已停止"
echo ""

# 2. 检查并创建必要文件
echo "[2/5] 检查配置文件..."
if [ ! -f "backend/.env" ]; then
    echo "创建 .env 文件..."
    cd backend
    cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
    cd ..
    echo "✓ .env 文件已创建"
else
    echo "✓ .env 文件已存在"
fi

# 3. 创建数据目录
echo "[3/5] 创建数据目录..."
mkdir -p backend/data
chmod -R 755 backend/data
echo "✓ 数据目录已创建"
echo ""

# 4. 查看之前的日志（如果容器还在）
echo "[4/5] 查看之前的错误日志..."
if docker ps -a | grep -q xyzrank-backend; then
    echo "之前的容器日志:"
    docker logs --tail=50 xyzrank-backend 2>&1 | head -30
    echo ""
    echo "删除旧容器..."
    docker rm -f xyzrank-backend 2>/dev/null || true
fi
echo ""

# 5. 重新启动
echo "[5/5] 重新启动服务..."
docker-compose -f $COMPOSE_FILE up -d
echo "✓ 服务已启动"
echo ""

echo "等待服务启动（10秒）..."
sleep 10

echo ""
echo "=========================================="
echo "查看服务状态"
echo "=========================================="
docker-compose -f $COMPOSE_FILE ps
echo ""

echo "查看最新日志:"
echo "  docker-compose -f $COMPOSE_FILE logs --tail=50 backend"
echo ""

echo "如果还在重启，请查看日志找出问题:"
echo "  docker-compose -f $COMPOSE_FILE logs backend"
echo ""

