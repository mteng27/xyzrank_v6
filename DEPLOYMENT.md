# 腾讯云轻量应用服务器部署指南

## 📋 部署概述

本指南将帮助你将 XYZRank 项目部署到腾讯云轻量应用服务器，包括：
- 后端 FastAPI 服务
- 前端静态页面
- Nginx 反向代理
- 定时任务调度
- 数据库配置

## 🖥️ 服务器要求

### 最低配置
- **CPU**: 2核
- **内存**: 2GB
- **系统**: Ubuntu 20.04+ / CentOS 7+
- **磁盘**: 20GB+

### 推荐配置
- **CPU**: 4核
- **内存**: 4GB
- **系统**: Ubuntu 22.04 LTS
- **磁盘**: 50GB+

## 📦 部署步骤

### 1. 服务器准备

#### 1.1 连接到服务器
```bash
ssh root@your-server-ip
```

#### 1.2 更新系统
```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# CentOS
yum update -y
```

#### 1.3 安装基础软件
```bash
# Ubuntu/Debian
apt install -y python3.10 python3.10-venv python3-pip nginx git curl

# CentOS
yum install -y python3 python3-pip nginx git curl
```

#### 1.4 安装 Playwright 依赖（用于爬虫）
```bash
# Ubuntu/Debian
apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2 libgbm1 libasound2

# CentOS
yum install -y nss nspr atk at-spi2-atk cups-libs libdrm \
  libxkbcommon libXcomposite libXdamage libXfixes libXrandr \
  mesa-libgbm alsa-lib
```

### 2. 项目部署

#### 2.1 创建项目目录
```bash
mkdir -p /opt/xyzrank
cd /opt/xyzrank
```

#### 2.2 上传项目文件

**方式A：使用 Git（推荐）**
```bash
# 在本地先提交到 Git
git init
git add .
git commit -m "Initial commit"

# 在服务器上克隆（需要先配置 Git 仓库）
git clone your-repo-url /opt/xyzrank
```

**方式B：使用 SCP 上传**
```bash
# 在本地执行
scp -r /Users/mateng/xyzrank_v6/* root@your-server-ip:/opt/xyzrank/
```

**方式C：使用 rsync（推荐，支持增量同步）**
```bash
# 在本地执行
rsync -avz --exclude '*.pyc' --exclude '__pycache__' --exclude '*.db' \
  /Users/mateng/xyzrank_v6/ root@your-server-ip:/opt/xyzrank/
```

#### 2.3 设置权限
```bash
chown -R www-data:www-data /opt/xyzrank
chmod -R 755 /opt/xyzrank
```

### 3. 后端配置

#### 3.1 创建虚拟环境
```bash
cd /opt/xyzrank/backend
python3 -m venv venv
source venv/bin/activate
```

#### 3.2 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

#### 3.3 配置环境变量
```bash
cd /opt/xyzrank/backend
cat > .env << EOF
APP_NAME=XYZRank API
ENVIRONMENT=production

# 数据库配置（使用 SQLite 或 MySQL）
DB_TYPE=sqlite
SQLITE_DB_PATH=xyzrank.db

# 如果使用 MySQL，取消注释以下配置
# DB_TYPE=mysql
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=xyzrank
# MYSQL_PASSWORD=your_password
# MYSQL_DB=xyzrank
EOF
```

#### 3.4 运行数据库迁移
```bash
cd /opt/xyzrank/backend
source venv/bin/activate

# 运行迁移脚本（添加排名字段）
python calculate_ranks_for_existing_data.py
```

### 4. 创建 Systemd 服务

#### 4.1 创建后端服务
```bash
cat > /etc/systemd/system/xyzrank-backend.service << 'EOF'
[Unit]
Description=XYZRank Backend API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/xyzrank/backend
Environment="PATH=/opt/xyzrank/backend/venv/bin"
ExecStart=/opt/xyzrank/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

#### 4.2 启动服务
```bash
systemctl daemon-reload
systemctl enable xyzrank-backend
systemctl start xyzrank-backend
systemctl status xyzrank-backend
```

### 5. Nginx 配置

#### 5.1 创建 Nginx 配置
```bash
cat > /etc/nginx/sites-available/xyzrank << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或IP

    # 前端静态文件
    location / {
        root /opt/xyzrank/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
EOF
```

#### 5.2 启用配置
```bash
# Ubuntu/Debian
ln -s /etc/nginx/sites-available/xyzrank /etc/nginx/sites-enabled/
nginx -t  # 测试配置
systemctl restart nginx

# CentOS
cp /etc/nginx/sites-available/xyzrank /etc/nginx/conf.d/xyzrank.conf
nginx -t
systemctl restart nginx
```

### 6. 防火墙配置

```bash
# Ubuntu/Debian (UFW)
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
```

### 7. SSL 证书（可选，推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx  # Ubuntu/Debian
# 或
yum install certbot python3-certbot-nginx  # CentOS

# 获取证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

## 🔄 更新部署

### 更新代码
```bash
cd /opt/xyzrank

# 方式1：Git 拉取
git pull

# 方式2：rsync 同步（从本地）
# 在本地执行：
# rsync -avz --exclude '*.pyc' --exclude '__pycache__' \
#   /Users/mateng/xyzrank_v6/ root@your-server-ip:/opt/xyzrank/
```

### 更新依赖
```bash
cd /opt/xyzrank/backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 运行数据库迁移
```bash
cd /opt/xyzrank/backend
source venv/bin/activate
alembic upgrade head
```

### 重启服务
```bash
systemctl restart xyzrank-backend
systemctl restart nginx
```

## 📊 监控和维护

### 查看服务状态
```bash
# 后端服务
systemctl status xyzrank-backend
journalctl -u xyzrank-backend -f  # 查看日志

# Nginx
systemctl status nginx
tail -f /var/log/nginx/error.log
```

### 查看定时任务
```bash
# 查看调度器日志
journalctl -u xyzrank-backend | grep "定时任务"
```

### 备份数据库
```bash
# SQLite
cp /opt/xyzrank/backend/xyzrank.db /opt/xyzrank/backup/xyzrank_$(date +%Y%m%d).db

# MySQL
mysqldump -u xyzrank -p xyzrank > /opt/xyzrank/backup/xyzrank_$(date +%Y%m%d).sql
```

## 🐛 故障排查

### 服务无法启动
```bash
# 检查服务状态
systemctl status xyzrank-backend

# 查看详细日志
journalctl -u xyzrank-backend -n 100

# 检查端口占用
netstat -tlnp | grep 8000
```

### 数据库连接失败
```bash
# 检查数据库文件权限
ls -la /opt/xyzrank/backend/xyzrank.db

# 检查 .env 配置
cat /opt/xyzrank/backend/.env
```

### Nginx 502 错误
```bash
# 检查后端服务是否运行
curl http://127.0.0.1:8000/health

# 检查 Nginx 配置
nginx -t
```

## 📝 注意事项

1. **安全配置**
   - 修改默认密码
   - 配置防火墙
   - 使用 HTTPS（推荐）
   - 限制 CORS 来源（生产环境）

2. **性能优化**
   - 调整 uvicorn workers 数量
   - 配置 Nginx 缓存
   - 使用 CDN（可选）

3. **数据备份**
   - 定期备份数据库
   - 配置自动备份脚本

4. **日志管理**
   - 配置日志轮转
   - 定期清理旧日志

## 🔗 相关文件

- `deploy.sh` - 自动化部署脚本
- `nginx.conf` - Nginx 配置文件
- `xyzrank-backend.service` - Systemd 服务文件

