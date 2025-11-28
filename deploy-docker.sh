#!/bin/bash
# XYZRank Docker 部署脚本
# 适用于 OpenCloudOS 8 / CentOS 8+ / Ubuntu 20.04+

set -e

echo "=========================================="
echo "XYZRank Docker 部署脚本"
echo "适用于: OpenCloudOS 8 + Docker 26"
echo "=========================================="
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    exit 1
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}Docker Compose 未安装，正在安装...${NC}"
    # 安装 Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose 安装完成${NC}"
fi

# 项目目录 - 自动检测当前目录或使用默认路径
if [ -f "docker-compose.yml" ]; then
    # 如果当前目录有 docker-compose.yml，使用当前目录
    PROJECT_DIR=$(pwd)
    echo -e "${GREEN}使用当前目录: $PROJECT_DIR${NC}"
elif [ -f "/opt/xyzrank_v6/docker-compose.yml" ]; then
    # 如果默认路径存在，使用默认路径
    PROJECT_DIR="/opt/xyzrank_v6"
    cd "$PROJECT_DIR"
    echo -e "${GREEN}使用默认目录: $PROJECT_DIR${NC}"
else
    # 否则使用当前目录
    PROJECT_DIR=$(pwd)
    echo -e "${YELLOW}使用当前目录: $PROJECT_DIR${NC}"
    echo -e "${YELLOW}请确保在项目根目录运行此脚本${NC}"
fi

echo -e "${GREEN}[1/6] 检查项目文件...${NC}"
cd "$PROJECT_DIR"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 未找到 docker-compose.yml 文件${NC}"
    echo "当前目录: $(pwd)"
    echo "请确保在项目根目录运行此脚本"
    echo ""
    echo "正确的运行方式:"
    echo "  cd /opt/xyzrank_v6"
    echo "  ./deploy-docker.sh"
    exit 1
fi
echo -e "${GREEN}✓ 项目文件检查完成${NC}"
echo -e "${GREEN}项目目录: $PROJECT_DIR${NC}"
echo ""

echo -e "${GREEN}[2/6] 配置环境变量...${NC}"
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo -e "${YELLOW}已创建 .env 文件，请编辑配置:${NC}"
        echo "  nano backend/.env"
        echo ""
        read -p "按 Enter 继续（或 Ctrl+C 退出编辑配置）..."
    else
        echo -e "${YELLOW}创建默认 .env 文件...${NC}"
        cat > backend/.env << EOF
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
    fi
fi
echo -e "${GREEN}✓ 环境变量配置完成${NC}"
echo ""

echo -e "${GREEN}[3/6] 创建必要目录...${NC}"
mkdir -p backend/data
mkdir -p nginx/conf.d
mkdir -p nginx/ssl
chmod -R 755 backend/data
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

echo -e "${GREEN}[4/6] 初始化数据库...${NC}"
if [ ! -f "backend/data/xyzrank.db" ]; then
    echo -e "${YELLOW}数据库不存在，将在首次启动时自动创建${NC}"
else
    echo -e "${GREEN}✓ 数据库已存在${NC}"
fi
echo ""

echo -e "${GREEN}[5/6] 构建 Docker 镜像...${NC}"
docker-compose build --no-cache
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

echo -e "${GREEN}[6/6] 启动服务...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ 服务启动完成${NC}"
echo ""

echo -e "${GREEN}[7/7] 等待服务就绪并初始化数据库...${NC}"
echo -e "${YELLOW}等待服务启动（30秒）...${NC}"
sleep 30

# 检查后端服务是否就绪
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose exec -T backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务已就绪${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}等待后端服务启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 5
done

# 初始化数据库
echo -e "${YELLOW}初始化数据库...${NC}"
if docker-compose exec -T backend alembic upgrade head 2>/dev/null; then
    echo -e "${GREEN}✓ 数据库初始化完成${NC}"
else
    echo -e "${YELLOW}⚠ 数据库初始化失败，可能需要手动执行：${NC}"
    echo "  docker-compose exec backend alembic upgrade head"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "服务状态:"
docker-compose ps
echo ""
echo "查看日志:"
echo "  docker-compose logs -f"
echo ""
echo "停止服务:"
echo "  docker-compose down"
echo ""
echo "重启服务:"
echo "  docker-compose restart"
echo ""
echo "访问地址:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo "  http://localhost"
echo ""
echo "如果数据库未自动初始化，请手动执行:"
echo "  docker-compose exec backend alembic upgrade head"
echo ""

