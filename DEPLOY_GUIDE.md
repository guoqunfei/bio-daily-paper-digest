# NCBI Eukaryota Pipeline - GitHub Actions 部署指南

---

## 1. run_pipeline_final.sh 修改说明

以下是为适配 GitHub Actions 环境所做的修改：

| 修改点 | 原内容 | 修改后 | 原因 |
|--------|--------|--------|------|
| 环境检查命令列表 | `python3.9` | `python3` | GitHub Actions 默认 Python 为 3.11/3.12，无需指定 3.9 |
| Python 包检查 | `python3.9 -c ...` | `python3 -c ...` | 同上 |
| 下载 wrapper 调用 | `python3.9 fetch_with_timeout.py` | `python3 fetch_with_timeout.py` | 同上 |
| Excel 生成调用 | `python3.9 generate_excel.py` | `python3 generate_excel.py` | 同上 |

---

## 2. GitHub Actions Workflow 文件

文件位置：`.github/workflows/ncbi-daily.yml`

已创建，主要特性：

- **触发器**：每天 UTC 02:00（北京时间 10:00）自动运行，支持 `workflow_dispatch` 手动触发
- **依赖安装**：自动安装 taxonkit、NCBI datasets CLI、jq
- **Python 环境**：使用 `actions/setup-python@v5` 配置 Python 3.12
- **缓存策略**：`actions/cache@v4` 缓存 taxonkit taxdump 数据库
- **Artifact 上传**：保留 90 天
- **自动提交**：`git-auto-commit-action` 提交结果到 `results/YYYY-MM-DD/` 目录
- **邮件通知**：成功/失败分别发送不同邮件

---

## 3. 邮件发送配置说明

### 3.1 需要在 GitHub Secrets 中配置的变量

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加以下变量：

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `SMTP_SERVER` | SMTP 服务器地址 | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 端口 | `587` (Gmail/Office365) 或 `465` |
| `SMTP_USER` | SMTP 用户名（邮箱地址） | `yourname@gmail.com` |
| `SMTP_PASSWORD` | SMTP 密码/应用密码 | `xxxx xxxx xxxx xxxx` |
| `EMAIL_TO` | 收件人地址 | `guoqunfei@genomics.cn` |
| `EMAIL_FROM` | 发件人地址（通常与 SMTP_USER 相同） | `yourname@gmail.com` |

### 3.2 Gmail 应用密码生成步骤

1. 开启两步验证：
   - 访问 https://myaccount.google.com/security
   - 找到"两步验证"并开启

2. 生成应用密码：
   - 访问 https://myaccount.google.com/apppasswords
   - 选择"应用"→"其他（自定义名称）"，输入 `GitHub Actions NCBI`
   - 点击"生成"，复制 16 位应用密码（如：`abcd efgh ijkl mnop`）

3. 将密码填入 GitHub Secret `SMTP_PASSWORD`（注意：填入时去掉空格）

### 3.3 Office365 / 企业邮箱配置

| 参数 | Office365 | 企业邮箱示例 |
|------|-----------|-------------|
| SMTP_SERVER | `smtp.office365.com` | `smtp.genomics.cn` |
| SMTP_PORT | `587` | `587` 或 `25` |
| SMTP_USER | `yourname@company.com` | `yourname@genomics.cn` |
| SMTP_PASSWORD | 邮箱密码或应用密码 | 邮箱密码 |

---

## 4. 首次部署后的测试步骤

### 4.1 推送到 GitHub

```bash
# 在项目根目录执行
git add run_pipeline_final.sh .github/workflows/ncbi-daily.yml
git commit -m "feat: add GitHub Actions daily pipeline"
git push origin main
```

### 4.2 配置 GitHub Secrets

按照上述 3.1 节的说明，在仓库 Settings → Secrets 中添加 6 个 Secrets。

### 4.3 手动触发测试

1. 打开仓库页面，点击 **Actions** 标签
2. 选择左侧 **NCBI Eukaryota Daily Pipeline**
3. 点击右上角 **Run workflow → Run workflow**
4. 等待运行完成（约 10-30 分钟）

### 4.4 验证邮件和结果

#### 验证邮件通知：
- **成功邮件**：检查邮箱是否收到标题为 `[NCBI Daily] YYYY-MM-DD 基因组摘要统计完成` 的邮件，附件应包含两个 Excel 文件
- **失败邮件**：如果运行失败，应收到 `[NCBI Daily ERROR] YYYY-MM-DD 运行失败` 邮件，内含错误信息和日志链接

#### 验证结果文件：
1. **Artifact 下载**：在 Actions 运行页面下方找到 Artifacts 区域，下载 `ncbi-results-YYYY-MM-DD`
2. **仓库内查看**：检查 `results/YYYY-MM-DD/` 目录是否包含以下文件：
   - `Eukaryota_assemblies_summary.xlsx`
   - `NCBI_Eukaryota_Taxonomy_Summary.xlsx`
   - `NCBI_Eukaryota_Taxonomy_Summary.txt`
   - `summary.txt`（运行摘要）
   - `pipeline_*.log`（运行日志）

#### 验证自动提交：
- 检查仓库的 Git 提交历史，确认有 `[NCBI Daily] YYYY-MM-DD pipeline results` 的自动提交

### 4.5 常见问题排查

| 问题 | 排查方法 |
|------|---------|
| 邮件未收到 | 检查 Secrets 配置是否正确，SMTP 端口是否为 587，Gmail 是否使用应用密码 |
| taxonkit 下载失败 | 检查 GitHub Actions 日志中的网络连接状态，确认能访问 GitHub releases |
| NCBI datasets 下载超时 | 这是正常的，脚本内置 300s 超时保护，检查超时后是否继续执行 |
| Excel 未生成 | 检查 Python pandas/openpyxl 是否安装成功，查看 pipeline 日志 |
| Artifact 未上传 | 检查 `actions/upload-artifact` 步骤日志，确认文件路径正确 |
