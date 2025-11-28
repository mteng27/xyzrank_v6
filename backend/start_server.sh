#!/bin/bash
# 启动后端服务

cd "$(dirname "$0")"

echo "=========================================="
echo "启动 XYZRank API 服务"
echo "=========================================="
echo ""
echo "服务将在 http://localhost:8000 启动"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


