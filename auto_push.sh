#!/bin/bash
set -e

echo "=========================================="
echo "  一键推送工具"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f ".github/workflows/ncbi-daily.yml" ]; then
    echo "错误: 请在 NCBI_Eukaryota_New 目录下运行此脚本"
    exit 1
fi

echo "步骤 1/3: 正在生成新的 GitHub PAT..."
echo ""
echo "请在浏览器中完成以下操作："
echo "1. 访问: https://github.com/settings/tokens/new"
echo "2. Note 填写: NCBI Pipeline Push"
echo "3. 勾选权限:"
echo "   - ✅ repo (完整仓库访问)"
echo "   - ✅ workflow (更新 GitHub Actions)"
echo "4. 点击 Generate token"
echo "5. 复制生成的 token"
echo ""

# 等待用户输入 PAT
read -s -p "粘贴你的新 PAT 后按回车: " PAT
echo ""

if [ -z "$PAT" ]; then
    echo "错误: PAT 不能为空"
    exit 1
fi

echo ""
echo "步骤 2/3: 正在推送代码..."

# 使用 PAT 推送
git remote set-url ncbi "https://guoqunfei:${PAT}@github.com/guoqunfei/NCBI_Eukaryota.git"

if git push ncbi main; then
    echo ""
    echo "✅ 推送成功!"
    echo ""
    echo "你可以去 GitHub 查看："
    echo "https://github.com/guoqunfei/NCBI_Eukaryota/actions"
else
    echo ""
    echo "❌ 推送失败"
    echo "请确认："
    echo "  - PAT 是否包含 'repo' 和 'workflow' 权限"
    echo "  - PAT 是否已经过期"
fi

# 恢复 remote URL（移除 PAT）
git remote set-url ncbi "https://github.com/guoqunfei/NCBI_Eukaryota.git"

echo ""
echo "步骤 3/3: 清理完成，PAT 已从配置中移除"
echo ""
echo "=========================================="
echo "  完成"
echo "=========================================="
