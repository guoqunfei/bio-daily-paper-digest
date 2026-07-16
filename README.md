# 🧬 Bio Daily Paper Digest

基因组学与结构变异领域 · 每日文献自动推送 + 用户反馈闭环 + 趋势分析

## 核心功能

### 文献推送
- **多源聚合**：PubMed / arXiv / Semantic Scholar
- **严格过滤**：关键词白名单 + 黑名单 + 相关性评分（1-10分）
- **中文总结**：LLM 强制中文输出，结构化字段（方法创新、核心指标、代码仓库、推荐操作）
- **来源分组**：📰 预印本 / 🏆 顶刊 / 🔬 专业期刊 / 📑 其他
- **邮件推送**：Table 布局兼容 QQ/Gmail/Outlook，纯文本 fallback

### 用户反馈闭环（两种模式）

#### 模式 A：Cloudflare Worker（推荐，零操作）
- 点击邮件中的 `[⭐有用]` → 自动记录，无需任何后续操作
- 次日推送自动根据你的兴趣调整
- 部署步骤见下方

#### 模式 B：GitHub Issue Fallback
- 点击邮件中的按钮 → 打开预填的 GitHub Issue → 点击 Submit
- 无需写代码，只需一次点击

### 趋势分析
- **30天趋势报告**：热点关键词、新兴工具、热门物种、高分文献时间线
- **个人待办**：标记"3天后提醒"的文献，到期自动在邮件头部显示
- **周度报告**：每周日自动生成完整趋势 Markdown

### 用户画像
- 每个收件人独立兴趣画像
- 基于 `star` 历史自动提取关键词权重
- 新文献含这些关键词时自动加分（最高 +3 分）
- 被 `ignore` 的文献不再推送

## 快速开始

### 1. 仓库设置

进入仓库 → **Settings → General → Issues** → ✅ Enable

创建 `feedback` 标签：Issues → Labels → New label
- Name: `feedback`
- Color: `#f9d0c4`
- Description: User feedback from email digest

### 2. 添加 Secrets

Settings → Secrets and variables → Actions → New repository secret：

| Secret | 说明 | 必需 |
|---|---|---|
| `LLM_API_KEY` | OpenAI / 兼容 API Key | ✅ |
| `LLM_BASE_URL` | API 基础地址（默认 https://api.openai.com/v1） | ❌ |
| `LLM_MODEL` | 模型名（默认 gpt-4o-mini） | ❌ |
| `SMTP_SERVER` | SMTP 服务器（如 smtp.gmail.com） | ✅ |
| `SMTP_PORT` | 端口（587 或 465） | ✅ |
| `SMTP_USER` | 发件邮箱 | ✅ |
| `SMTP_PASSWORD` | 授权码 / App Password | ✅ |
| `EMAIL_TO` | 收件人（支持逗号分隔多邮箱） | ✅ |
| `EMAIL_FROM` | 发件人（默认同 SMTP_USER） | ❌ |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API Key | ❌ |
| `PAT` | Personal Access Token（git push 用） | ❌ |
| `FEEDBACK_MODE` | `worker` 或 `issue`（默认 `issue`） | ❌ |
| `FEEDBACK_WORKER_URL` | Cloudflare Worker URL（模式 A 必需） | ❌ |

### 3. 配置领域关键词

编辑 `config/keywords.yaml`：

```yaml
core_keywords:
  - "structural variation"
  - "genome assembly"
  - "Myrmecia"
  - "pig genome"
  - "antifreeze protein"
  - "Hi-C"

high_value_keywords:
  - "myrmecia"        # 标题出现 +3 分
  - "bull ant"
  - "pig genome"

exclude_keywords:
  - "clinical trial"    # 出现即丢弃
  - "cancer"
  - "patient"
```

### 4. 部署 Cloudflare Worker（模式 A，零操作反馈）

**为什么需要 Worker？**

邮件是静态 HTML，无法直接调用 GitHub API。Worker 作为公网中转，接收点击请求后自动创建 GitHub Issue。

**部署步骤（5分钟）：**

1. 注册 [Cloudflare](https://cloudflare.com)（免费）
2. 左侧菜单 → **Workers & Pages** → **Create a Service**
3. 选择 **HTTP handler**，粘贴 `cloudflare-worker.js` 中的代码
4. 点击 **Save and Deploy**
5. 进入 Worker → **Settings → Variables**
   - 添加 `GITHUB_TOKEN`：你的 GitHub Personal Access Token（需要 `repo` 权限）
   - 添加 `REPO_OWNER`：`guoqunfei`
   - 添加 `REPO_NAME`：`bio-daily-paper-digest`
6. 复制 Worker URL（如 `https://bio-digest.yourname.workers.dev`）
7. 填入仓库 Secrets：`FEEDBACK_WORKER_URL`
8. 设置 `FEEDBACK_MODE` = `worker`

**不想部署 Worker？** 保持 `FEEDBACK_MODE` = `issue`（默认），使用 GitHub Issue 预填链接，只需一次点击 Submit。

### 5. 手动测试

Actions → Daily Literature Digest → **Run workflow**

### 6. 使用反馈功能

**模式 A（Worker）：**
- 收到邮件 → 点击 `[⭐有用]` → 看到 "✅ 反馈已记录" 页面 → 完成

**模式 B（Issue）：**
- 收到邮件 → 点击 `[⭐有用]` → 浏览器打开 GitHub Issue 创建页面 → 点击 **Submit new issue** → 完成

**3天后提醒：**
- 点击 `[⏰ 3天后提醒]` → 同样流程
- 3天后该文献自动出现在邮件头部 "⏰ 待跟进提醒" 板块

**不再推送：**
- 点击 `[🚫 不再推送]` → 该文献不再出现在你的推送中

## 文件结构

```
config/keywords.yaml          # 关键词配置
scripts/
  main.py                     # 主入口
  config.py                   # 配置管理
  fetch_papers.py             # 多源抓取 + 过滤 + 用户兴趣加分
  summarize.py                # LLM 中文结构化总结
  email_sender.py             # 邮件发送（分组 + 交互链接）
  dedup.py                    # 去重存储
  github_feedback.py          # GitHub Issues 处理 + 多用户画像
  source_classifier.py      # 来源分类（预印本/顶刊/专业期刊）
  trend_analyzer.py           # 趋势分析 + 个人待办
  trend_report.py             # 周趋势报告生成
.github/workflows/
  daily-literature-digest.yml # 每日定时（09:07 CST）
  weekly-trend.yml            # 每周趋势（周日 10:00 CST）
cloudflare-worker.js          # 零操作反馈接收器（可选）
output/                       # 历史归档
  YYYY-MM-DD/
    digest.md                 # 邮件版
    digest_all.md             # 完整版
    papers.json               # 原始数据
    trend_30d.md              # 30天趋势报告
  trend-reports/
    weekly-YYYY-MM-DD.md      # 周趋势报告
.paper-digest-cache/          # GitHub Actions cache
  seen_papers.json            # 去重记录
  multi_user_feedback.json    # 多用户画像 + 待跟进列表
```

## 反馈系统工作原理

### 模式 A（Worker，零操作）

```
用户点击邮件中的 [⭐有用]
        ↓
链接: https://your-worker.workers.dev/?action=star&paper=doi:xxx&user=email
        ↓
Cloudflare Worker 接收请求
        ↓
Worker 调用 GitHub API 创建 Issue（带 feedback 标签）
        ↓
用户看到 "✅ 反馈已记录" 页面（无需任何操作）
        ↓
次日 Actions 运行：读取 Issue → 更新用户画像 → 关闭 Issue
        ↓
新文献含用户 star 过的关键词 → 自动 +1~3 分
```

### 模式 B（Issue，一次点击）

```
用户点击邮件中的 [⭐有用]
        ↓
链接: https://github.com/.../issues/new?title=[STAR]doi:xxx&body=...&labels=feedback
        ↓
GitHub 页面已预填所有内容
        ↓
用户点击 Submit new issue（一次点击）
        ↓
次日 Actions 运行：读取 Issue → 更新用户画像 → 关闭 Issue
```

### 3天后提醒实现

```
用户点击 [⏰ 3天后提醒]
        ↓
记录创建时间到 multi_user_feedback.json
        ↓
每日 Actions 检查：today - created_at >= 3天？
        ↓
到期的文献 → 邮件头部 "⏰ 待跟进提醒" 板块显示
        ↓
用户点击文献标题重新阅读
        ↓
（可选）再次标记 done → 从提醒列表移除
```

## 多用户支持

`EMAIL_TO` 支持逗号分隔多个邮箱：

```yaml
EMAIL_TO: "guoqunfei@genomics.cn,teammate1@genomics.cn,teammate2@genomics.cn"
```

每个用户：
- 独立兴趣画像（基于各自 star 历史）
- 独立忽略列表
- 独立待跟进提醒

**注意**：当前邮件发送给所有收件人相同内容。如需个性化内容，需为每个用户单独运行 workflow。

## 趋势分析示例

### 30天趋势报告（自动生成）

```markdown
# 📈 近30天文献趋势报告 | 2026-07-16

共监控 **127** 篇文献

## 🔥 热点关键词 TOP20
- **genome assembly**: 23 篇
- **structural variation**: 18 篇
- **Hi-C**: 15 篇
- **Myrmecia**: 8 篇
- **antifreeze protein**: 6 篇

## 🛠️ 新兴工具/方法
- **hifiasm**: 12 次出现
- **yahs**: 9 次出现
- **sniffles2**: 7 次出现

## ⭐ 高分文献时间线（≥8分）
- **2026-07-15** | [Chromosome-level genome assembly of...](...) | **9/10** | 利用hifiasm完成牛蚁属染色体级组装...
- **2026-07-14** | [SV-Scanner: A deep learning...](...) | **8/10** | 基于Transformer的SV检测模型...
```

## 常见问题

**Q: 相关性分数为什么超过 10？**
A: 已修复。代码中强制 `min(score, 10)`，Prompt 中也明确要求 1-10 整数。

**Q: 一句话总结为什么还是英文/复制摘要？**
A: 已增强 Prompt 约束：明确禁止复制摘要、要求 40-60 字中文、给出正/反例。同时增加 JSON 解析失败的重试机制。

**Q: 我不想部署 Cloudflare Worker，能用吗？**
A: 可以。保持默认 `FEEDBACK_MODE=issue`，使用 GitHub Issue 预填链接，只需点击 Submit。

**Q: 如何查看我的兴趣画像？**
A: 在仓库 `.paper-digest-cache/multi_user_feedback.json` 中查看，或查看 GitHub Issues 历史。

**Q: 可以支持飞书/Slack/钉钉推送吗？**
A: 可以扩展 `email_sender.py` 增加 webhook 发送，但当前版本仅支持邮件。
