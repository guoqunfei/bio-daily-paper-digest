#!/bin/bash
set -e

echo "=========================================="
echo "  GitHub Workflow 推送工具"
echo "=========================================="
echo ""
echo "请确保你已经生成了包含 'workflow' 权限的 GitHub PAT"
echo "生成地址: https://github.com/settings/tokens/new"
echo ""
echo "需要勾选的权限:"
echo "  - repo (完整仓库访问)"
echo "  - workflow (更新 GitHub Actions workflow)"
echo ""
read -s -p "请输入新的 GitHub PAT (输入时不会显示): " PAT
echo ""

if [ -z "$PAT" ]; then
    echo "错误: PAT 不能为空"
    exit 1
fi

echo ""
echo "正在推送代码..."

# 临时设置 remote URL
git remote set-url ncbi "https://guoqunfei:${PAT}@github.com/guoqunfei/NCBI_Eukaryota.git"

# 推送代码
if git push ncbi main; then
    echo ""
    echo "✅ 推送成功!"
else
    echo ""
    echo "❌ 推送失败，请检查 PAT 权限是否正确"
fi

# 恢复 remote URL（移除 PAT）
git remote set-url ncbi "https://github.com/guoqunfei/NCBI_Eukaryota.git"

echo ""
echo "Remote URL 已恢复为安全状态"
