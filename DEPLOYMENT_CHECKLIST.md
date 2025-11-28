# 部署检查清单

## 📋 部署前准备

### 本地准备
- [ ] 确认项目代码已提交到 Git（或准备好上传）
- [ ] 确认数据库文件已备份（如果有）
- [ ] 确认 `.env` 配置已准备好
- [ ] 确认所有依赖已记录在 `requirements.txt`

### 服务器准备
- [ ] 已获取服务器 IP 地址和 root 密码
- [ ] 已配置 SSH 密钥（推荐）或准备好密码
- [ ] 确认服务器系统版本（Ubuntu 20.04+ 或 CentOS 7+）
- [ ] 确认服务器有足够资源（2核2GB+）

## 🚀 部署步骤

### 1. 连接服务器
```bash
ssh root@your-server-ip
```

### 2. 上传项目文件

**推荐方式：rsync（支持增量同步）**
```bash
# 在本地执行
rsync -avz --exclude '*.pyc' --exclude '__pycache__' --exclude '*.db' \
  --exclude 'venv' --exclude '.git' \
  /Users/mateng/xyzrank_v6/ root@your-server-ip:/opt/xyzrank/
```

### 3. 运行部署脚本
```bash
# 在服务器上执行
cd /opt/xyzrank
chmod +x deploy.sh
./deploy.sh
```

### 4. 配置检查
- [ ] 后端服务运行正常：`systemctl status xyzrank-backend`
- [ ] Nginx 运行正常：`systemctl status nginx`
- [ ] API 可访问：`curl http://localhost:8000/health`
- [ ] 前端可访问：浏览器打开 `http://your-server-ip`

### 5. 数据导入（如果需要）
```bash
cd /opt/xyzrank/backend
source venv/bin/activate

# 如果有 CSV 数据需要导入
python import_data_simple.py
```

### 6. 配置定时任务
- [ ] 确认定时任务已启动：`journalctl -u xyzrank-backend | grep "定时任务"`
- [ ] 确认调度器正常运行

## 🔧 配置调整

### 修改 API 地址（如果需要）
如果前端和后端不在同一域名，需要修改前端：
```javascript
// 在 frontend/index.html 中
const API_BASE = 'http://your-api-domain.com';
```

### 配置 CORS（如果需要）
在 `backend/app/main.py` 中修改：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://your-frontend-domain.com"],  # 指定前端域名
    ...
)
```

## ✅ 部署后验证

### 功能测试
- [ ] 前端页面可以正常打开
- [ ] 可以加载播客列表
- [ ] 可以搜索播客
- [ ] 可以查看播客详情
- [ ] 趋势图正常显示
- [ ] 排名信息正常显示

### 性能测试
- [ ] API 响应时间 < 1秒
- [ ] 前端加载时间 < 3秒
- [ ] 定时任务正常运行

## 🔄 后续维护

### 日常更新
```bash
# 使用更新脚本
cd /opt/xyzrank
./update.sh
```

### 查看日志
```bash
# 后端日志
journalctl -u xyzrank-backend -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 备份数据
```bash
# 备份数据库
cp /opt/xyzrank/backend/xyzrank.db /opt/xyzrank/backup/xyzrank_$(date +%Y%m%d).db
```

## 🆘 常见问题

### 问题1：服务无法启动
```bash
# 检查日志
journalctl -u xyzrank-backend -n 50

# 检查端口
netstat -tlnp | grep 8000

# 检查权限
ls -la /opt/xyzrank/backend/
```

### 问题2：Nginx 502 错误
```bash
# 检查后端服务
systemctl status xyzrank-backend
curl http://127.0.0.1:8000/health

# 检查 Nginx 配置
nginx -t
```

### 问题3：前端无法连接后端
- 检查 API_BASE 配置
- 检查 CORS 设置
- 检查防火墙规则

## 📞 技术支持

如遇到问题，请检查：
1. 服务日志：`journalctl -u xyzrank-backend -f`
2. Nginx 日志：`tail -f /var/log/nginx/error.log`
3. 系统资源：`htop` 或 `free -h`

