# 部署检查清单

## ✅ 部署前检查

### 服务器环境
- [ ] 操作系统：OpenCloudOS 8 / CentOS 8+ / Ubuntu 20.04+
- [ ] Docker 已安装：`docker --version`
- [ ] Docker Compose 已安装：`docker-compose --version` 或 `docker compose version`
- [ ] 有 root 权限或 sudo 权限
- [ ] 端口 80、443、8000 未被占用

### 项目文件
- [ ] 项目已下载到服务器（`/opt/xyzrank_v6`）
- [ ] `docker-compose.yml` 文件存在
- [ ] `Dockerfile` 文件存在
- [ ] `backend/` 目录存在
- [ ] `frontend/` 目录存在
- [ ] `nginx/` 目录存在

---

## 🚀 部署步骤

### 1. 准备环境

```bash
# 安装 Git（如果未安装）
yum install -y git

# 或使用 wget 下载
yum install -y wget unzip
wget https://github.com/mteng27/xyzrank_v6/archive/refs/heads/main.zip
unzip main.zip
mv xyzrank_v6-main xyzrank_v6
```

### 2. 运行部署脚本

```bash
cd /opt/xyzrank_v6
chmod +x deploy-docker.sh
./deploy-docker.sh
```

### 3. 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.cn.yml ps

# 检查健康状态
curl http://localhost/health

# 检查 API
curl http://localhost/api/podcasts/
```

---

## 🔍 部署后检查

### 服务状态
- [ ] 后端服务运行正常：`docker ps | grep xyzrank-backend`
- [ ] Nginx 服务运行正常：`docker ps | grep xyzrank-nginx`
- [ ] 无容器重启：`docker ps` 显示 `Up` 状态

### 功能测试
- [ ] 前端页面可访问：浏览器打开 `http://your-ip`
- [ ] API 健康检查通过：`curl http://localhost/health`
- [ ] API 返回数据：`curl http://localhost/api/podcasts/`
- [ ] 数据库文件已创建：`ls -la backend/data/xyzrank.db`

### 日志检查
- [ ] 后端日志无错误：`docker-compose logs backend | grep -i error`
- [ ] Nginx 日志正常：`docker-compose logs nginx | tail -20`

---

## 🐛 常见问题

### 问题 1: 容器一直重启

**检查日志:**
```bash
docker logs xyzrank-backend --tail=100
```

**常见原因:**
- `.env` 文件缺失 → 运行 `./fix-restart.sh`
- 数据目录权限问题 → `chmod -R 755 backend/data`
- 数据库迁移失败 → 手动执行 `alembic upgrade head`

### 问题 2: 无法访问前端

**检查:**
```bash
# 检查 Nginx 容器
docker ps | grep nginx

# 检查端口
netstat -tlnp | grep 80

# 检查 Nginx 日志
docker-compose logs nginx
```

### 问题 3: API 返回 502

**检查:**
```bash
# 检查后端服务
docker-compose exec backend curl http://localhost:8000/health

# 检查网络连接
docker network inspect xyzrank_xyzrank-network
```

---

## 📝 维护命令

### 查看日志
```bash
# 所有服务
docker-compose -f docker-compose.cn.yml logs -f

# 仅后端
docker-compose -f docker-compose.cn.yml logs -f backend

# 仅 Nginx
docker-compose -f docker-compose.cn.yml logs -f nginx
```

### 重启服务
```bash
# 重启所有
docker-compose -f docker-compose.cn.yml restart

# 仅重启后端
docker-compose -f docker-compose.cn.yml restart backend
```

### 更新代码
```bash
cd /opt/xyzrank_v6
git pull origin main
docker-compose -f docker-compose.cn.yml build --no-cache
docker-compose -f docker-compose.cn.yml up -d
```

### 备份数据
```bash
# 备份数据库
cp backend/data/xyzrank.db backend/data/backup_$(date +%Y%m%d_%H%M%S).db
```

---

## ✅ 部署成功标志

- ✅ 所有容器状态为 `Up`
- ✅ 健康检查通过：`curl http://localhost/health` 返回 `{"status":"ok"}`
- ✅ 前端页面正常显示
- ✅ API 返回数据
- ✅ 无错误日志

---

**部署完成后，请按照此清单逐项检查！**
