# 快速部署指南

## 🚀 一键部署（推荐）

### 在服务器上执行

```bash
# 1. 上传部署脚本到服务器
# 在本地执行：
scp deploy.sh root@your-server-ip:/root/

# 2. 上传项目文件（使用 rsync，推荐）
rsync -avz --exclude '*.pyc' --exclude '__pycache__' --exclude '*.db' \
  --exclude 'venv' --exclude '.git' \
  /Users/mateng/xyzrank_v6/ root@your-server-ip:/opt/xyzrank/

# 3. 在服务器上运行部署脚本
ssh root@your-server-ip
chmod +x /root/deploy.sh
/root/deploy.sh
```

## 📋 手动部署步骤

### 1. 上传项目文件

**方式A：使用 rsync（推荐，支持增量同步）**
```bash
# 在本地执行
rsync -avz --exclude '*.pyc' --exclude '__pycache__' --exclude '*.db' \
  --exclude 'venv' --exclude '.git' \
  /Users/mateng/xyzrank_v6/ root@your-server-ip:/opt/xyzrank/
```

**方式B：使用 SCP**
```bash
# 在本地执行
scp -r /Users/mateng/xyzrank_v6/* root@your-server-ip:/opt/xyzrank/
```

**方式C：使用 Git（需要先配置仓库）**
```bash
# 在服务器上执行
cd /opt
git clone your-repo-url xyzrank
```

### 2. 运行部署脚本

```bash
# 在服务器上执行
cd /opt/xyzrank
chmod +x deploy.sh
./deploy.sh
```

### 3. 配置域名（可选）

如果使用域名，修改 Nginx 配置：
```bash
nano /etc/nginx/sites-available/xyzrank
# 修改 server_name 为你的域名
systemctl restart nginx
```

### 4. 配置 SSL（可选）

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## 🔄 更新项目

### 方式1：使用更新脚本（推荐）

```bash
# 在服务器上执行
cd /opt/xyzrank
chmod +x update.sh
./update.sh
```

### 方式2：手动更新

```bash
# 1. 上传最新代码（在本地执行）
rsync -avz --exclude '*.pyc' --exclude '__pycache__' --exclude '*.db' \
  --exclude 'venv' /Users/mateng/xyzrank_v6/ root@your-server-ip:/opt/xyzrank/

# 2. 更新依赖和重启（在服务器上执行）
cd /opt/xyzrank/backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
alembic upgrade head
systemctl restart xyzrank-backend
```

## 📊 验证部署

### 检查服务状态
```bash
# 后端服务
systemctl status xyzrank-backend

# Nginx
systemctl status nginx

# 测试 API
curl http://localhost:8000/health
curl http://localhost/api/podcasts/?limit=5
```

### 访问服务
- 前端：http://your-server-ip
- API：http://your-server-ip/api
- 文档：http://your-server-ip/docs

## 🛠️ 常用命令

```bash
# 查看后端日志
journalctl -u xyzrank-backend -f

# 重启服务
systemctl restart xyzrank-backend
systemctl restart nginx

# 停止服务
systemctl stop xyzrank-backend

# 查看服务状态
systemctl status xyzrank-backend
```

## ⚠️ 注意事项

1. **防火墙**：确保开放 80 和 443 端口
2. **域名**：如果使用域名，需要配置 DNS 解析
3. **数据库**：首次部署后需要导入数据
4. **定时任务**：服务启动后会自动开始定时抓取

