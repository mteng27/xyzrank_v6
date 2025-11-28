#!/bin/bash
# 快速查看日志脚本

echo "=========================================="
echo "查看 XYZRank 服务日志"
echo "=========================================="
echo ""

COMPOSE_FILE="docker-compose.cn.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

echo "使用配置文件: $COMPOSE_FILE"
echo ""

echo "后端服务日志（最近50行）:"
echo "----------------------------------------"
docker-compose -f $COMPOSE_FILE logs --tail=50 backend
echo ""

echo "Nginx 服务日志（最近20行）:"
echo "----------------------------------------"
docker-compose -f $COMPOSE_FILE logs --tail=20 nginx
echo ""

echo "查看实时日志:"
echo "  docker-compose -f $COMPOSE_FILE logs -f backend"
echo ""

echo "进入容器调试:"
echo "  docker-compose -f $COMPOSE_FILE exec backend bash"
echo ""

