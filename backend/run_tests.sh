#!/bin/bash
# 运行 API 测试脚本

echo "=========================================="
echo "运行 API 测试"
echo "=========================================="
echo ""

# 检查服务是否运行
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ 服务未运行！"
    echo "请先启动服务: uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ 服务正在运行"
echo ""

# 运行测试脚本
python test_api.py

