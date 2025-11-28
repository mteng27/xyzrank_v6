# 故障排查指南

## Git Clone 卡住问题

### 问题现象
```bash
git clone https://github.com/mteng27/xyzrank_v6.git
Cloning into 'xyzrank_v6'...
# 一直卡在这里，没有进度
```

### 解决方案

#### 方案 1：使用浅克隆（推荐）

```bash
# 只克隆最新版本，不包含历史记录
git clone --depth 1 https://github.com/mteng27/xyzrank_v6.git

# 如果还是慢，可以设置超时
git clone --depth 1 --progress https://github.com/mteng27/xyzrank_v6.git
```

#### 方案 2：使用 wget 下载 ZIP（最快）

```bash
# 安装 wget 和 unzip（如果未安装）
yum install -y wget unzip

# 下载 ZIP 文件
cd /opt
wget https://github.com/mteng27/xyzrank_v6/archive/refs/heads/main.zip

# 解压
unzip main.zip

# 重命名
mv xyzrank_v6-main xyzrank_v6
cd xyzrank_v6
```

#### 方案 3：检查网络连接

```bash
# 测试 GitHub 连接
ping github.com

# 测试 DNS 解析
nslookup github.com

# 如果无法访问，可能需要配置代理或使用镜像
```

#### 方案 4：使用 GitHub 镜像（如果在中国大陆）

```bash
# 使用 Gitee 镜像（如果有）
# 或者使用 GitHub 加速服务

# 方法：修改 hosts 文件
echo "140.82.112.3 github.com" >> /etc/hosts
echo "140.82.112.4 github.com" >> /etc/hosts

# 然后重试
git clone --depth 1 https://github.com/mteng27/xyzrank_v6.git
```

#### 方案 5：增加 Git 超时时间

```bash
# 设置更长的超时时间
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999

# 然后重试
git clone --depth 1 https://github.com/mteng27/xyzrank_v6.git
```

---

## 推荐操作步骤

### 如果 Git Clone 卡住超过 2 分钟：

1. **按 Ctrl+C 取消当前操作**

2. **使用 wget 下载 ZIP（最快最可靠）**：

```bash
# 取消当前操作
# 按 Ctrl+C

# 安装工具
yum install -y wget unzip

# 下载项目
cd /opt
wget https://github.com/mteng27/xyzrank_v6/archive/refs/heads/main.zip

# 解压
unzip main.zip
mv xyzrank_v6-main xyzrank_v6
cd xyzrank_v6

# 验证文件
ls -la docker-compose.yml Dockerfile deploy-docker.sh

# 运行部署
chmod +x deploy-docker.sh
./deploy-docker.sh
```

---

## 其他常见问题

### Docker 未安装

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | bash
systemctl start docker
systemctl enable docker
```

### Docker Compose 未安装

```bash
# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 端口被占用

```bash
# 检查端口
netstat -tlnp | grep 80
netstat -tlnp | grep 8000

# 如果被占用，可以修改 docker-compose.yml 中的端口映射
```

---

## 快速部署命令（完整版）

如果 Git Clone 有问题，使用这个完整命令序列：

```bash
# 1. 安装必要工具
yum install -y wget unzip

# 2. 下载项目（使用 wget）
cd /opt
wget https://github.com/mteng27/xyzrank_v6/archive/refs/heads/main.zip

# 3. 解压
unzip main.zip
mv xyzrank_v6-main xyzrank_v6
cd xyzrank_v6

# 4. 配置环境变量
cd backend
cat > .env << 'EOF'
APP_NAME=XYZRank API
ENVIRONMENT=production
DATABASE_URL=sqlite+aiosqlite:///./data/xyzrank.db
EOF
cd ..

# 5. 运行部署
chmod +x deploy-docker.sh
./deploy-docker.sh

# 6. 初始化数据库（等待 30 秒后）
sleep 30
docker-compose exec backend alembic upgrade head
```

---

**如果还有问题，请提供具体的错误信息！**

