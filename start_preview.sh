#!/bin/bash
# 启动前后端预览

echo "=========================================="
echo "XYZRank 本地预览"
echo "=========================================="
echo ""

# 检查后端服务
echo "检查后端服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务运行中: http://localhost:8000"
else
    echo "⚠️  后端服务未运行，正在启动..."
    cd backend
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
    sleep 3
    echo "✅ 后端服务已启动"
    cd ..
fi

echo ""

# 检查前端服务
echo "检查前端服务..."
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ 前端服务运行中: http://localhost:8080"
else
    echo "⚠️  前端服务未运行，正在启动..."
    cd frontend
    nohup python3 -m http.server 8080 > /tmp/frontend.log 2>&1 &
    sleep 2
    echo "✅ 前端服务已启动"
    cd ..
fi

echo ""
echo "=========================================="
echo "访问地址:"
echo "  前端页面: http://localhost:8080"
echo "  后端API:  http://localhost:8000"
echo "  API文档:  http://localhost:8000/docs"
echo "=========================================="
echo ""

# 尝试在浏览器中打开
if command -v open > /dev/null; then
    open http://localhost:8080
    echo "✅ 已在浏览器中打开前端页面"
elif command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8080
    echo "✅ 已在浏览器中打开前端页面"
else
    echo "请手动在浏览器中访问: http://localhost:8080"
fi

echo ""
echo "按 Ctrl+C 停止服务"


