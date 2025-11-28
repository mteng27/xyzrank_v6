# XYZRank 快速部署指南（OpenCloudOS 8）

> 适用于：腾讯轻量云 OpenCloudOS 8 + Docker 26

---

## 🚀 一键部署（推荐）

### 方式一：使用完整部署脚本

```bash
# 1. 安装 Git（如果未安装）
yum install -y git

# 2. 克隆项目
cd /opt
git clone https://github.com/mteng27/xyzrank_v6.git
cd xyzrank_v6

# 3. 运行 Docker 部署脚本
chmod +x deploy-docker.sh
./deploy-docker.sh

# 4. 初始化数据库
docker-compose exec backend alembic upgrade head
```

### 方式二：手动部署

如果无法使用 Git，可以手动上传文件：

```bash
# 1. 在本地打包项目（排除不必要的文件）
cd /Users/mateng/xyzrank_v6
tar -czf xyzrank_v6.tar.gz \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='node_modules' \
  .

# 2. 上传到服务器
scp xyzrank_v6.tar.gz root@your-server-ip:/opt/

# 3. 在服务器上解压
cd /opt
tar -xzf xyzrank_v6.tar.gz
mv xyzrank_v6 xyzrank
cd xyzrank

# 4. 运行部署脚本
chmod +x deploy-docker.sh
./deploy-docker.sh
```

---

## 📦 安装必要工具

### 1. 安装 Git

```bash
yum install -y git
```

### 2. 安装 Docker（如果未安装）

```bash
# 安装 Docker
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io

# 启动 Docker
systemctl start docker
systemctl enable docker

# 验证安装
docker --version
```

### 3. 安装 Docker Compose

```bash
# 下载 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

---

## 🔧 完整部署流程

### 步骤 1：准备环境

```bash
# 更新系统
yum update -y

# 安装基础工具
yum install -y git curl wget

# 安装 Docker（如果未安装）
# 参考上面的 Docker 安装步骤
```

### 步骤 2：获取项目代码

```bash
# 方式 A：使用 Git（推荐）
cd /opt
git clone https://github.com/mteng27/xyzrank_v6.git
cd xyzrank_v6

# 方式 B：使用 wget 下载 ZIP（如果 Git 不可用）
cd /opt
wget https://github.com/mteng27/xyzrank_v6/archive/refs/heads/main.zip
unzip main.zip
mv xyzrank_v6-main xyzrank_v6
cd xyzrank_v6
```

### 步骤 3：配置环境变量

```bash
cd backend

# 创建 .env 文件
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF

cd ..
```

### 步骤 4：运行部署

```bash
# 添加执行权限
chmod +x deploy-docker.sh

# 运行部署脚本
./deploy-docker.sh
```

### 步骤 5：初始化数据库

```bash
# 等待服务启动（约 30 秒）
sleep 30

# 初始化数据库
docker-compose exec backend alembic upgrade head
```

### 步骤 6：验证部署

```bash
# 检查服务状态
docker-compose ps

# 测试健康检查
curl http://localhost/health

# 测试 API
curl http://localhost/api/podcasts/
```

---

## 🔍 常见问题

### 问题 1：Git 未安装

```bash
yum install -y git
```

### 问题 2：Docker 未安装

参考上面的 Docker 安装步骤，或使用：

```bash
# 使用官方安装脚本（推荐）
curl -fsSL https://get.docker.com | bash
systemctl start docker
systemctl enable docker
```

### 问题 3：Docker Compose 未安装

```bash
# 下载最新版本
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 问题 4：端口被占用

```bash
# 检查端口占用
netstat -tlnp | grep 80
netstat -tlnp | grep 8000

# 如果被占用，修改 docker-compose.yml 中的端口映射
```

### 问题 5：权限问题

```bash
# 确保以 root 用户运行
whoami  # 应该显示 root

# 如果使用普通用户，需要添加到 docker 组
usermod -aG docker $USER
newgrp docker
```

---

## 📝 部署后检查清单

- [ ] Git 已安装：`git --version`
- [ ] Docker 已安装：`docker --version`
- [ ] Docker Compose 已安装：`docker-compose --version`
- [ ] 项目代码已下载
- [ ] 环境变量已配置
- [ ] 服务已启动：`docker-compose ps`
- [ ] 健康检查通过：`curl http://localhost/health`
- [ ] 前端可访问：浏览器打开 `http://your-server-ip`
- [ ] API 可访问：`curl http://localhost/api/podcasts/`

---

## 🆘 获取帮助

如果遇到问题：

1. 查看服务日志：`docker-compose logs -f`
2. 检查容器状态：`docker-compose ps`
3. 查看部署文档：`cat DOCKER_DEPLOY.md`
4. GitHub Issues: https://github.com/mteng27/xyzrank_v6/issues

---

**祝部署顺利！** 🚀

