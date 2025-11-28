#!/bin/bash
# 推送到 GitHub 的便捷脚本

echo "=========================================="
echo "XYZRank - 推送到 GitHub"
echo "=========================================="
echo ""

# 检查是否已配置远程仓库
if git remote | grep -q "^origin$"; then
    echo "✅ 已检测到远程仓库配置"
    git remote -v
    echo ""
    read -p "是否使用现有远程仓库推送？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
else
    echo "⚠️  未检测到远程仓库配置"
    echo ""
    echo "请提供 GitHub 仓库地址："
    echo "  格式: https://github.com/用户名/仓库名.git"
    echo "  或: git@github.com:用户名/仓库名.git"
    echo ""
    read -p "GitHub 仓库地址: " repo_url
    
    if [ -z "$repo_url" ]; then
        echo "❌ 未提供仓库地址，已取消"
        exit 1
    fi
    
    echo ""
    echo "添加远程仓库..."
    git remote add origin "$repo_url"
    echo "✅ 已添加远程仓库: $repo_url"
    echo ""
fi

# 检查当前分支
current_branch=$(git branch --show-current)
echo "当前分支: $current_branch"
echo ""

# 确认推送
read -p "确认推送到 GitHub？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "正在推送到 GitHub..."
echo ""

# 推送
if git push -u origin "$current_branch"; then
    echo ""
    echo "=========================================="
    echo "✅ 推送成功！"
    echo "=========================================="
    echo ""
    echo "📦 仓库信息:"
    git remote get-url origin
    echo ""
    echo "🌐 你可以在 GitHub 上查看代码了"
else
    echo ""
    echo "❌ 推送失败"
    echo ""
    echo "可能的原因:"
    echo "  1. 仓库地址不正确"
    echo "  2. 没有推送权限"
    echo "  3. 需要先创建 GitHub 仓库"
    echo ""
    echo "💡 提示:"
    echo "  如果仓库不存在，请先在 GitHub 上创建仓库"
    echo "  然后重新运行此脚本"
fi

