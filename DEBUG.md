# 故障排查指南

## 后端服务一直重启

### 问题现象
```
xyzrank-backend   Restarting (1) 18 seconds ago
```

### 排查步骤

#### 1. 查看后端日志

```bash
# 查看最近日志
docker-compose -f docker-compose.cn.yml logs --tail=100 backend

# 或者使用脚本
./check-logs.sh
```

#### 2. 常见原因和解决方案

##### 原因 1: 数据库文件权限问题

```bash
# 检查数据目录权限
ls -la backend/data/

# 修复权限
chmod -R 755 backend/data
chown -R 1000:1000 backend/data  # 如果知道容器用户ID

# 重启服务
docker-compose -f docker-compose.cn.yml restart backend
```

##### 原因 2: 环境变量文件缺失或格式错误

```bash
# 检查 .env 文件
cat backend/.env

# 确保文件存在且格式正确
cd backend
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
cd ..

# 重启服务
docker-compose -f docker-compose.cn.yml restart backend
```

##### 原因 3: 数据库迁移失败

```bash
# 进入容器手动执行迁移
docker-compose -f docker-compose.cn.yml exec backend bash

# 在容器内执行
alembic upgrade head

# 如果失败，查看详细错误
alembic current
alembic history
```

##### 原因 4: Python 依赖问题

```bash
# 查看完整错误日志
docker-compose -f docker-compose.cn.yml logs backend | grep -i error

# 重新构建镜像
docker-compose -f docker-compose.cn.yml build --no-cache backend
docker-compose -f docker-compose.cn.yml up -d
```

##### 原因 5: 端口被占用

```bash
# 检查端口占用
netstat -tlnp | grep 8000

# 如果被占用，修改 docker-compose.cn.yml 中的端口映射
# 或者停止占用端口的服务
```

#### 3. 进入容器调试

```bash
# 进入后端容器
docker-compose -f docker-compose.cn.yml exec backend bash

# 在容器内检查
ls -la /app
ls -la /app/data
cat /app/.env
python -c "from app.main import app; print('OK')"

# 手动启动服务查看错误
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 4. 完全重置（最后手段）

```bash
# 停止并删除所有容器
docker-compose -f docker-compose.cn.yml down

# 删除数据目录（注意：会丢失数据）
rm -rf backend/data/*

# 重新构建和启动
docker-compose -f docker-compose.cn.yml build --no-cache
docker-compose -f docker-compose.cn.yml up -d

# 等待后初始化数据库
sleep 30
docker-compose -f docker-compose.cn.yml exec backend alembic upgrade head
```

---

## 快速诊断命令

```bash
# 1. 查看服务状态
docker-compose -f docker-compose.cn.yml ps

# 2. 查看后端日志
docker-compose -f docker-compose.cn.yml logs --tail=50 backend

# 3. 查看容器详细信息
docker inspect xyzrank-backend

# 4. 检查健康状态
docker-compose -f docker-compose.cn.yml exec backend curl http://localhost:8000/health

# 5. 查看资源使用
docker stats xyzrank-backend
```

---

## 常见错误信息

### 错误: "No such file or directory: '/app/.env'"

**解决方案:**
```bash
cd backend
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
cd ..
docker-compose -f docker-compose.cn.yml restart backend
```

### 错误: "Can't open database file"

**解决方案:**
```bash
mkdir -p backend/data
chmod -R 755 backend/data
docker-compose -f docker-compose.cn.yml restart backend
```

### 错误: "ModuleNotFoundError"

**解决方案:**
```bash
# 重新构建镜像
docker-compose -f docker-compose.cn.yml build --no-cache backend
docker-compose -f docker-compose.cn.yml up -d
```

---

**如果问题仍未解决，请提供完整的错误日志！**

