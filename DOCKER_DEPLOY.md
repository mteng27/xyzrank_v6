# XYZRank Docker 部署指南

> 适用于：腾讯轻量云 OpenCloudOS 8 + Docker 26

---

## 📋 快速开始

### 1. 准备服务器

确保服务器已安装：
- ✅ Docker 26+
- ✅ Docker Compose（或 Docker Compose V2）

### 2. 克隆项目

```bash
cd /opt
git clone https://github.com/mteng27/xyzrank_v6.git
cd xyzrank_v6
```

### 3. 配置环境变量

```bash
cd backend
cp .env.example .env
nano .env
```

最小配置（使用 SQLite）：
```env
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
```

### 4. 运行部署脚本

```bash
chmod +x deploy-docker.sh
sudo ./deploy-docker.sh
```

### 5. 初始化数据库（首次部署）

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行数据库迁移
alembic upgrade head

# 退出容器
exit
```

---

## 🐳 Docker 架构

```
┌─────────────────┐
│   Nginx (80)    │  ← 前端静态文件 + API 反向代理
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│Frontend│ │Backend│  ← FastAPI (8000)
│(Volume)│ │(Docker)│
└────────┘ └───────┘
```

---

## 📁 目录结构

```
/opt/xyzrank/
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile              # 后端镜像构建文件
├── backend/
│   ├── .env               # 环境变量配置
│   ├── data/              # 数据目录（SQLite 数据库）
│   └── ...                # 应用代码
├── frontend/
│   └── index.html         # 前端页面
└── nginx/
    ├── nginx.conf         # Nginx 主配置
    └── conf.d/
        └── xyzrank.conf   # 站点配置
```

---

## 🔧 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f backend    # 只看后端日志
docker-compose logs -f nginx      # 只看 Nginx 日志
```

### 数据库操作

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行数据库迁移
alembic upgrade head

# 创建新迁移
alembic revision --autogenerate -m "描述"

# 查看数据库（SQLite）
sqlite3 backend/data/xyzrank.db
```

### 更新代码

```bash
# 1. 拉取最新代码
cd /opt/xyzrank
git pull origin main

# 2. 重新构建镜像
docker-compose build

# 3. 重启服务
docker-compose up -d
```

### 备份数据

```bash
# 备份 SQLite 数据库
cp backend/data/xyzrank.db backend/data/backup_$(date +%Y%m%d).db

# 或使用 Docker
docker-compose exec backend cp /app/data/xyzrank.db /app/data/backup_$(date +%Y%m%d).db
```

---

## 🔒 配置 HTTPS

### 1. 获取 SSL 证书

使用 Certbot（Let's Encrypt）：

```bash
# 安装 Certbot
yum install -y certbot python3-certbot-nginx

# 获取证书（需要先配置域名解析）
certbot certonly --standalone -d your-domain.com
```

### 2. 配置 Nginx

编辑 `nginx/conf.d/xyzrank.conf`，取消注释 HTTPS 配置：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... 其他配置
}
```

### 3. 复制证书到容器

```bash
# 复制证书文件
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# 重启 Nginx
docker-compose restart nginx
```

---

## 🔍 故障排查

### 服务无法启动

```bash
# 查看容器状态
docker-compose ps

# 查看详细日志
docker-compose logs backend
docker-compose logs nginx

# 检查端口占用
netstat -tlnp | grep 8000
netstat -tlnp | grep 80
```

### 数据库连接问题

```bash
# 检查数据库文件权限
ls -la backend/data/

# 进入容器检查
docker-compose exec backend bash
ls -la /app/data/
```

### Nginx 502 错误

```bash
# 检查后端服务
docker-compose exec backend curl http://localhost:8000/health

# 检查 Nginx 配置
docker-compose exec nginx nginx -t
```

### 容器无法访问网络

```bash
# 检查 Docker 网络
docker network ls
docker network inspect xyzrank_xyzrank-network
```

---

## 📊 性能优化

### 1. 资源限制

编辑 `docker-compose.yml`：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 2. 日志管理

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. 健康检查

已在 `docker-compose.yml` 中配置，自动重启不健康的容器。

---

## 🔄 升级和维护

### 定期更新

```bash
# 1. 备份数据
cp backend/data/xyzrank.db backend/data/backup_$(date +%Y%m%d).db

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建
docker-compose build --no-cache

# 4. 重启服务
docker-compose up -d

# 5. 运行数据库迁移（如果有）
docker-compose exec backend alembic upgrade head
```

### 清理未使用的资源

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器和网络
docker system prune
```

---

## 📝 检查清单

部署完成后，请检查：

- [ ] 后端服务运行：`docker-compose ps`
- [ ] 健康检查通过：`curl http://localhost/health`
- [ ] 前端页面可访问：浏览器打开 `http://your-ip`
- [ ] API 可访问：`curl http://localhost/api/podcasts/`
- [ ] 日志正常：`docker-compose logs --tail=50`
- [ ] 数据库文件存在：`ls -la backend/data/`

---

## 🆘 获取帮助

- 查看日志：`docker-compose logs -f`
- 检查容器：`docker-compose ps`
- 进入容器：`docker-compose exec backend bash`
- GitHub Issues: https://github.com/mteng27/xyzrank_v6/issues

---

**祝部署顺利！** 🚀

