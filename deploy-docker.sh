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
BLUE='\033[0;34m'
NC='\033[0m'

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    exit 1
fi

# 项目目录 - 自动检测
if [ -f "docker-compose.yml" ]; then
    PROJECT_DIR=$(pwd)
    echo -e "${GREEN}✓ 使用当前目录: $PROJECT_DIR${NC}"
elif [ -f "/opt/xyzrank_v6/docker-compose.yml" ]; then
    PROJECT_DIR="/opt/xyzrank_v6"
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✓ 使用默认目录: $PROJECT_DIR${NC}"
else
    PROJECT_DIR=$(pwd)
    echo -e "${YELLOW}⚠ 使用当前目录: $PROJECT_DIR${NC}"
    echo -e "${YELLOW}请确保在项目根目录运行此脚本${NC}"
fi

cd "$PROJECT_DIR"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker 未安装，请先安装 Docker${NC}"
    echo "安装命令: curl -fsSL https://get.docker.com | bash"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${YELLOW}Docker Compose 未安装，正在安装...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose 安装完成${NC}"
fi

echo ""
echo -e "${GREEN}[1/7] 检查项目文件...${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 未找到 docker-compose.yml 文件${NC}"
    echo "当前目录: $(pwd)"
    exit 1
fi
echo -e "${GREEN}✓ 项目文件检查完成${NC}"
echo ""

echo -e "${GREEN}[2/7] 配置环境变量...${NC}"
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}创建 .env 文件...${NC}"
    mkdir -p backend
    cat > backend/.env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DB_TYPE=sqlite
SQLITE_DB_PATH=data/xyzrank.db
EOF
    echo -e "${GREEN}✓ .env 文件已创建（使用 SQLite）${NC}"
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi
echo ""

echo -e "${GREEN}[3/7] 创建必要目录...${NC}"
mkdir -p backend/data
mkdir -p nginx/conf.d
mkdir -p nginx/ssl
chmod -R 755 backend/data
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

echo -e "${GREEN}[4/7] 选择构建方式...${NC}"
if [ -f "docker-compose.cn.yml" ]; then
    read -p "是否使用国内镜像源加速构建？(y/n，默认y) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        COMPOSE_FILE="docker-compose.cn.yml"
        echo -e "${GREEN}✓ 使用国内镜像源构建${NC}"
    else
        COMPOSE_FILE="docker-compose.yml"
        echo -e "${GREEN}✓ 使用默认源构建${NC}"
    fi
else
    COMPOSE_FILE="docker-compose.yml"
    echo -e "${GREEN}✓ 使用默认配置${NC}"
fi
echo ""

echo -e "${GREEN}[5/7] 构建 Docker 镜像...${NC}"
echo -e "${YELLOW}这可能需要几分钟时间，请耐心等待...${NC}"
if docker-compose -f $COMPOSE_FILE build --no-cache; then
    echo -e "${GREEN}✓ 镜像构建完成${NC}"
else
    echo -e "${RED}镜像构建失败，请检查错误信息${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}[6/7] 启动服务...${NC}"
docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
docker-compose -f $COMPOSE_FILE up -d
echo -e "${GREEN}✓ 服务启动完成${NC}"
echo ""

echo -e "${GREEN}[7/7] 等待服务就绪并初始化数据库...${NC}"
echo -e "${YELLOW}等待服务启动（最多60秒）...${NC}"

MAX_RETRIES=12
RETRY_COUNT=0
SERVICE_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    if docker-compose -f $COMPOSE_FILE exec -T backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务已就绪${NC}"
        SERVICE_READY=true
        break
    fi
    
    # 检查容器是否在运行
    if ! docker ps | grep -q xyzrank-backend; then
        echo -e "${RED}容器已停止，查看日志:${NC}"
        docker-compose -f $COMPOSE_FILE logs --tail=30 backend
        exit 1
    fi
    
    echo -e "${YELLOW}等待后端服务启动... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
done

if [ "$SERVICE_READY" = false ]; then
    echo -e "${RED}服务启动超时，查看日志:${NC}"
    docker-compose -f $COMPOSE_FILE logs --tail=50 backend
    echo ""
    echo -e "${YELLOW}请手动检查日志: docker-compose -f $COMPOSE_FILE logs backend${NC}"
    exit 1
fi

# 初始化数据库
echo -e "${YELLOW}初始化数据库...${NC}"
if docker-compose -f $COMPOSE_FILE exec -T backend alembic upgrade head 2>&1; then
    echo -e "${GREEN}✓ 数据库初始化完成${NC}"
else
    echo -e "${YELLOW}⚠ 数据库初始化可能失败，请手动执行:${NC}"
    echo "  docker-compose -f $COMPOSE_FILE exec backend alembic upgrade head"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "服务状态:"
docker-compose -f $COMPOSE_FILE ps
echo ""
echo "查看日志:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "停止服务:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""
echo "重启服务:"
echo "  docker-compose -f $COMPOSE_FILE restart"
echo ""
echo "访问地址:"
SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
echo "  http://$SERVER_IP"
echo "  http://localhost"
echo ""
