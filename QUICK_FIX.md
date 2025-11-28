# 快速修复指南

## 容器一直重启的问题

### 立即解决方案

#### 方法 1: 使用修复脚本（推荐）

```bash
cd /opt/xyzrank_v6

# 拉取最新代码（修复了 version 警告）
git pull origin main

# 运行修复脚本
chmod +x fix-restart.sh
./fix-restart.sh
```

#### 方法 2: 手动修复

```bash
cd /opt/xyzrank_v6

# 1. 强制停止所有容器
docker-compose -f docker-compose.cn.yml down
docker rm -f xyzrank-backend xyzrank-nginx 2>/dev/null || true

# 2. 查看之前的错误日志
docker logs xyzrank-backend 2>&1 | tail -50

# 3. 确保配置文件存在
cd backend
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
cd ..

# 4. 创建数据目录
mkdir -p backend/data
chmod -R 755 backend/data

# 5. 重新启动
docker-compose -f docker-compose.cn.yml up -d

# 6. 查看日志
docker-compose -f docker-compose.cn.yml logs -f backend
```

### 查看日志（即使容器在重启）

```bash
# 方法 1: 查看容器日志（不需要容器运行）
docker logs xyzrank-backend --tail=100

# 方法 2: 查看所有日志
docker logs xyzrank-backend 2>&1 | tail -100

# 方法 3: 实时查看（会显示重启循环）
docker logs -f xyzrank-backend
```

### 常见错误和解决方案

#### 错误 1: "No such file or directory: '/app/.env'"

```bash
cd /opt/xyzrank_v6/backend
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
cd ..
docker-compose -f docker-compose.cn.yml restart backend
```

#### 错误 2: "Can't open database file"

```bash
mkdir -p /opt/xyzrank_v6/backend/data
chmod -R 777 /opt/xyzrank_v6/backend/data
docker-compose -f docker-compose.cn.yml restart backend
```

#### 错误 3: "ModuleNotFoundError" 或导入错误

```bash
# 重新构建镜像
docker-compose -f docker-compose.cn.yml build --no-cache backend
docker-compose -f docker-compose.cn.yml up -d
```

#### 错误 4: "Port already in use"

```bash
# 检查端口占用
netstat -tlnp | grep 8000

# 停止占用端口的服务或修改 docker-compose.cn.yml 中的端口
```

### 完全重置（最后手段）

```bash
cd /opt/xyzrank_v6

# 1. 停止并删除所有
docker-compose -f docker-compose.cn.yml down -v
docker rm -f xyzrank-backend xyzrank-nginx 2>/dev/null || true

# 2. 清理数据（注意：会丢失数据）
rm -rf backend/data/*

# 3. 确保配置文件
cd backend
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
cd ..

# 4. 重新构建和启动
docker-compose -f docker-compose.cn.yml build --no-cache
docker-compose -f docker-compose.cn.yml up -d

# 5. 等待并初始化
sleep 30
docker-compose -f docker-compose.cn.yml exec backend alembic upgrade head
```

---

## 修复 version 警告

```bash
cd /opt/xyzrank_v6

# 拉取最新代码（已修复）
git pull origin main

# 或者手动编辑文件，删除第一行的 version: '3.8'
```

---

## 诊断命令

```bash
# 1. 查看容器状态
docker ps -a | grep xyzrank

# 2. 查看容器退出代码
docker inspect xyzrank-backend | grep -A 5 "State"

# 3. 查看完整日志
docker logs xyzrank-backend 2>&1

# 4. 进入容器（如果可能）
docker exec -it xyzrank-backend bash

# 5. 检查文件挂载
docker inspect xyzrank-backend | grep -A 10 "Mounts"
```

---

**请先执行 `docker logs xyzrank-backend --tail=100` 查看错误信息！**

