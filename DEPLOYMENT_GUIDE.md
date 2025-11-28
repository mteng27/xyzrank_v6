# XYZRank 完整部署指南

> 最后更新: 2025-01-XX
> 
> 本指南提供从零开始部署 XYZRank 项目的完整步骤，适用于腾讯云轻量应用服务器。

---

## 📋 目录

1. [部署概述](#部署概述)
2. [服务器准备](#服务器准备)
3. [项目部署](#项目部署)
4. [服务配置](#服务配置)
5. [域名和SSL](#域名和ssl)
6. [维护和更新](#维护和更新)
7. [故障排查](#故障排查)

---

## 🎯 部署概述

### 系统架构

```
用户请求
    ↓
Nginx (反向代理 + 静态文件服务)
    ↓
FastAPI 后端 (端口 8000)
    ↓
SQLite/MySQL 数据库
```

### 部署清单

- ✅ 后端 FastAPI 服务
- ✅ 前端静态页面
- ✅ Nginx 反向代理
- ✅ Systemd 服务管理
- ✅ 定时任务调度
- ✅ 日志管理

---

## 🖥️ 服务器准备

### 1. 服务器要求

**最低配置**
- CPU: 2核
- 内存: 2GB
- 系统: Ubuntu 20.04+ / CentOS 7+
- 磁盘: 20GB+

**推荐配置**
- CPU: 4核
- 内存: 4GB
- 系统: Ubuntu 22.04 LTS
- 磁盘: 50GB+

### 2. 连接到服务器

```bash
ssh root@your-server-ip
```

### 3. 更新系统

```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# CentOS
yum update -y
```

### 4. 安装基础软件

```bash
# Ubuntu/Debian
apt install -y python3.10 python3.10-venv python3-pip nginx git curl

# CentOS
yum install -y python3 python3-pip nginx git curl
```

---

## 📦 项目部署

### 方式一：使用自动化脚本（推荐）

#### 1. 下载部署脚本

```bash
# 如果项目已在服务器上
cd /opt
git clone https://github.com/mteng27/xyzrank_v6.git
cd xyzrank_v6

# 或者直接下载部署脚本
wget https://raw.githubusercontent.com/mteng27/xyzrank_v6/main/deploy.sh
chmod +x deploy.sh
```

#### 2. 配置环境变量

编辑 `.env` 文件（如果使用 MySQL）：

```bash
cd backend
cp .env.example .env
nano .env
```

配置内容：
```env
APP_NAME=XYZRank API
ENVIRONMENT=production

# 数据库配置（SQLite 或 MySQL）
# SQLite（默认，无需配置）
# DATABASE_URL=sqlite+aiosqlite:///./xyzrank.db

# MySQL（生产环境推荐）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=xyzrank
MYSQL_PASSWORD=your_password
MYSQL_DB=xyzrank
MYSQL_ECHO=false
```

#### 3. 运行部署脚本

```bash
sudo ./deploy.sh
```

脚本会自动完成：
- 安装系统依赖
- 创建项目目录
- 配置 Python 虚拟环境
- 安装项目依赖
- 配置数据库
- 设置 Nginx
- 配置 Systemd 服务

### 方式二：手动部署

#### 1. 创建项目目录

```bash
mkdir -p /opt/xyzrank
cd /opt/xyzrank
```

#### 2. 克隆项目

```bash
git clone https://github.com/mteng27/xyzrank_v6.git .
```

#### 3. 配置后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 初始化数据库
alembic upgrade head
```

#### 4. 配置前端

前端文件位于 `frontend/index.html`，无需额外配置。

---

## ⚙️ 服务配置

### 1. Systemd 服务配置

创建服务文件 `/etc/systemd/system/xyzrank.service`：

```ini
[Unit]
Description=XYZRank FastAPI Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/xyzrank/backend
Environment="PATH=/opt/xyzrank/backend/venv/bin"
ExecStart=/opt/xyzrank/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
systemctl daemon-reload
systemctl enable xyzrank
systemctl start xyzrank
systemctl status xyzrank
```

### 2. Nginx 配置

创建配置文件 `/etc/nginx/sites-available/xyzrank`：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或IP

    # 前端静态文件
    location / {
        root /opt/xyzrank/frontend;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # 后端 API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

启用配置：

```bash
ln -s /etc/nginx/sites-available/xyzrank /etc/nginx/sites-enabled/
nginx -t  # 测试配置
systemctl reload nginx
```

### 3. 防火墙配置

```bash
# Ubuntu/Debian (ufw)
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

---

## 🔒 域名和 SSL

### 1. 域名解析

在域名服务商处添加 A 记录，指向服务器 IP。

### 2. 申请 SSL 证书

使用 Let's Encrypt 免费证书：

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

### 3. 自动续期

证书会自动续期，可通过以下命令测试：

```bash
certbot renew --dry-run
```

---

## 🔄 维护和更新

### 更新项目代码

使用更新脚本：

```bash
cd /opt/xyzrank
./update.sh
```

或手动更新：

```bash
cd /opt/xyzrank
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
systemctl restart xyzrank
```

### 查看日志

```bash
# 服务日志
journalctl -u xyzrank -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 数据库备份

```bash
# SQLite
cp /opt/xyzrank/backend/xyzrank.db /opt/xyzrank/backend/backup/xyzrank_$(date +%Y%m%d).db

# MySQL
mysqldump -u xyzrank -p xyzrank > /opt/xyzrank/backend/backup/xyzrank_$(date +%Y%m%d).sql
```

---

## 🔧 故障排查

### 服务无法启动

```bash
# 检查服务状态
systemctl status xyzrank

# 查看详细日志
journalctl -u xyzrank -n 100

# 检查端口占用
netstat -tlnp | grep 8000
```

### Nginx 502 错误

```bash
# 检查后端服务是否运行
curl http://127.0.0.1:8000/health

# 检查 Nginx 配置
nginx -t

# 查看 Nginx 错误日志
tail -f /var/log/nginx/error.log
```

### 数据库连接问题

```bash
# 检查数据库文件权限
ls -la /opt/xyzrank/backend/xyzrank.db

# 测试数据库连接
cd /opt/xyzrank/backend
source venv/bin/activate
python -c "from app.db.session import AsyncSessionFactory; import asyncio; asyncio.run(AsyncSessionFactory().__aenter__())"
```

### 定时任务不执行

```bash
# 检查服务日志中的定时任务信息
journalctl -u xyzrank | grep scheduler

# 重启服务
systemctl restart xyzrank
```

---

## 📝 快速检查清单

部署完成后，请检查以下项目：

- [ ] 后端服务运行正常：`systemctl status xyzrank`
- [ ] 健康检查通过：`curl http://localhost:8000/health`
- [ ] Nginx 配置正确：`nginx -t`
- [ ] 前端页面可访问：浏览器打开 `http://your-domain.com`
- [ ] API 可访问：浏览器打开 `http://your-domain.com/api/podcasts/`
- [ ] 定时任务已启动：查看服务日志
- [ ] SSL 证书已配置（如果使用域名）
- [ ] 防火墙规则已配置

---

## 🆘 获取帮助

如果遇到问题：

1. 查看项目文档：`README.md`、`DEPLOYMENT.md`
2. 查看服务日志：`journalctl -u xyzrank -f`
3. 检查 GitHub Issues：https://github.com/mteng27/xyzrank_v6/issues

---

## 📚 相关文档

- [README.md](./README.md) - 项目概述和快速开始
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 详细部署文档
- [QUICK_DEPLOY.md](./QUICK_DEPLOY.md) - 快速部署指南
- [SPEC.md](./SPEC.md) - 项目规范文档

---

**祝部署顺利！** 🚀

