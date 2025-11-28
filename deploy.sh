#!/bin/bash
# XYZRank 项目部署脚本
# 用于腾讯云轻量应用服务器

set -e  # 遇到错误立即退出

echo "=========================================="
echo "XYZRank 项目部署脚本"
echo "=========================================="
echo ""

# 配置变量
PROJECT_DIR="/opt/xyzrank"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_USER="www-data"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    exit 1
fi

# 步骤1：安装系统依赖
echo -e "${GREEN}[1/8] 安装系统依赖...${NC}"
if command -v apt &> /dev/null; then
    apt update
    apt install -y python3.10 python3.10-venv python3-pip nginx git curl
    apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
      libxfixes3 libxrandr2 libgbm1 libasound2
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip nginx git curl
    yum install -y nss nspr atk at-spi2-atk cups-libs libdrm \
      libxkbcommon libXcomposite libXdamage libXfixes libXrandr \
      mesa-libgbm alsa-lib
else
    echo -e "${RED}不支持的系统，请手动安装依赖${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 系统依赖安装完成${NC}"
echo ""

# 步骤2：创建项目目录
echo -e "${GREEN}[2/8] 创建项目目录...${NC}"
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/backup"
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

# 步骤3：检查项目文件
echo -e "${GREEN}[3/8] 检查项目文件...${NC}"
if [ ! -d "$BACKEND_DIR" ] || [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}⚠️  项目文件不存在，请先上传项目文件到 $PROJECT_DIR${NC}"
    echo "可以使用以下方式上传："
    echo "  1. Git: git clone your-repo $PROJECT_DIR"
    echo "  2. SCP: scp -r local_path/* root@server:$PROJECT_DIR/"
    echo "  3. rsync: rsync -avz local_path/ root@server:$PROJECT_DIR/"
    exit 1
fi
echo -e "${GREEN}✓ 项目文件检查完成${NC}"
echo ""

# 步骤4：设置 Python 虚拟环境
echo -e "${GREEN}[4/8] 设置 Python 虚拟环境...${NC}"
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ 虚拟环境设置完成${NC}"
echo ""

# 步骤5：安装 Playwright
echo -e "${GREEN}[5/8] 安装 Playwright 浏览器...${NC}"
playwright install chromium
echo -e "${GREEN}✓ Playwright 安装完成${NC}"
echo ""

# 步骤6：配置环境变量
echo -e "${GREEN}[6/8] 配置环境变量...${NC}"
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cat > "$BACKEND_DIR/.env" << EOF
APP_NAME=XYZRank API
ENVIRONMENT=production

# 数据库配置
DB_TYPE=sqlite
SQLITE_DB_PATH=xyzrank.db

# MySQL 配置（如果使用 MySQL，取消注释）
# DB_TYPE=mysql
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=xyzrank
# MYSQL_PASSWORD=your_password
# MYSQL_DB=xyzrank
EOF
    echo -e "${YELLOW}⚠️  已创建 .env 文件，请根据需要修改配置${NC}"
fi
echo -e "${GREEN}✓ 环境变量配置完成${NC}"
echo ""

# 步骤7：运行数据库迁移
echo -e "${GREEN}[7/8] 运行数据库迁移...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
if [ -f "calculate_ranks_for_existing_data.py" ]; then
    python calculate_ranks_for_existing_data.py || echo -e "${YELLOW}⚠️  迁移脚本执行失败，请检查${NC}"
fi
echo -e "${GREEN}✓ 数据库迁移完成${NC}"
echo ""

# 步骤8：创建 Systemd 服务
echo -e "${GREEN}[8/8] 创建 Systemd 服务...${NC}"
cat > /etc/systemd/system/xyzrank-backend.service << EOF
[Unit]
Description=XYZRank Backend API Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable xyzrank-backend
echo -e "${GREEN}✓ Systemd 服务创建完成${NC}"
echo ""

# 步骤9：配置 Nginx
echo -e "${GREEN}[9/9] 配置 Nginx...${NC}"
read -p "请输入域名或IP地址（直接回车使用IP）: " DOMAIN
DOMAIN=${DOMAIN:-localhost}

cat > /etc/nginx/sites-available/xyzrank << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # 前端静态文件
    location / {
        root $FRONTEND_DIR;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    # API 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }
}
EOF

# 启用配置
if [ -d "/etc/nginx/sites-enabled" ]; then
    ln -sf /etc/nginx/sites-available/xyzrank /etc/nginx/sites-enabled/
else
    cp /etc/nginx/sites-available/xyzrank /etc/nginx/conf.d/xyzrank.conf
fi

# 测试配置
nginx -t && systemctl restart nginx
echo -e "${GREEN}✓ Nginx 配置完成${NC}"
echo ""

# 步骤10：设置权限
echo -e "${GREEN}[10/10] 设置文件权限...${NC}"
chown -R $SERVICE_USER:$SERVICE_USER "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
echo -e "${GREEN}✓ 权限设置完成${NC}"
echo ""

# 启动服务
echo -e "${GREEN}启动服务...${NC}"
systemctl start xyzrank-backend
sleep 3
systemctl status xyzrank-backend --no-pager

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 部署完成！${NC}"
echo "=========================================="
echo ""
echo "📊 服务状态："
echo "  后端服务: systemctl status xyzrank-backend"
echo "  Nginx: systemctl status nginx"
echo ""
echo "🌐 访问地址："
echo "  前端页面: http://$DOMAIN"
echo "  后端API: http://$DOMAIN/api"
echo "  API文档: http://$DOMAIN/docs"
echo ""
echo "📝 常用命令："
echo "  查看日志: journalctl -u xyzrank-backend -f"
echo "  重启服务: systemctl restart xyzrank-backend"
echo "  停止服务: systemctl stop xyzrank-backend"
echo ""

