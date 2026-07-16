# 🧬 Bio Daily Paper Digest

每日自动获取、归纳、总结生命科学领域（基因组学、结构变异等）最新文献，并通过邮件推送。支持每周趋势分析和用户交互式反馈。

## 功能特性

- **多源文献获取**：PubMed / arXiv / Semantic Scholar
- **LLM 智能总结**：使用 gpt-5.5 进行结构化分析（一句话总结、方法创新、核心指标、推荐操作）
- **关键词外部配置**：通过 `config/keywords.yaml` 配置核心关键词、高价值关键词和排除黑名单
- **智能去重**：基于 DOI / arXiv ID / PMID / 标题 Hash 的 JSON 持久化去重
- **用户反馈与画像**：邮件内嵌交互按钮（⭐有用 / ⏰3天后提醒 / 🚫不再推送），GitHub Issue 自动处理，多用户兴趣画像加权
- **待跟进提醒**：支持标记 follow-up，到期自动在邮件中提醒
- **每周趋势报告**：每周日自动汇总近7天文献生成趋势报告
- **HTML 邮件推送**：Table 布局兼容 QQ/Gmail/Outlook，支持纯文本 fallback，多收件人
- **GitHub Actions 自动运行**：每日 UTC 01:07（北京时间 09:07）自动执行

## 技术架构

```
bio-daily-paper-digest/
├── .github/workflows/
│   ├── daily-literature-digest.yml  # 每日文献摘要工作流
│   └── weekly-trend.yml             # 每周趋势报告工作流
├── config/
│   └── keywords.yaml                # 关键词与推送控制配置（可热更新）
├── scripts/
│   ├── config.py                    # 集中配置管理（解析 keywords.yaml）
│   ├── fetch_papers.py              # 多源文献获取 + 关键词评分过滤
│   ├── dedup.py                     # JSON 持久化去重（兼容 Actions cache）
│   ├── summarize.py                 # LLM 结构化总结 + 用户兴趣上下文校准
│   ├── email_sender.py              # HTML 邮件发送 + 交互链接
│   ├── github_feedback.py           # GitHub Issue 反馈处理 + 多用户画像
│   ├── trend_report.py              # 周趋势报告生成
│   └── main.py                      # 主程序入口（9步完整流程）
├── output/                          # 每日综述输出目录
├── .paper-digest-cache/             # 去重和用户反馈持久化缓存
├── requirements.txt                 # Python 依赖
└── README.md
```

## 主程序流程

```
[Step 0] 处理用户反馈 Issues (STAR/FOLLOW_UP/IGNORE)
[Step 1] 从 PubMed/arXiv/Semantic Scholar 获取文献
[Step 2] 去重（DOI/arXiv ID/PMID/标题 Hash）
[Step 3] 关键词评分过滤（核心+1，标题+2，高价值+3，兴趣画像加分，黑名单排除）
[Step 4] 反馈过滤（跳过用户标记 ignore 的文献）
[Step 5] LLM 结构化总结（含用户历史兴趣上下文校准）
[Step 6] 按 LLM 相关性评分排序，取前 N 篇发邮件
[Step 7] 生成 Markdown 归档（完整版 + 邮件版 + papers.json）
[Step 8] 标记已见 + 保存去重和用户反馈状态
[Step 9] 发送邮件（含待跟进提醒）
```

## 部署指南

### 1. 创建 GitHub 仓库

在 GitHub 创建新仓库 `bio-daily-paper-digest`（已自动创建）。

### 2. 配置 GitHub Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加以下变量：

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `LLM_API_KEY` | LLM API Key | `sk-...` |
| `LLM_BASE_URL` | LLM API Base URL | `https://dcsapi.dcs.cloud/api/aigress/unified/v1` |
| `LLM_MODEL` | LLM 模型名称 | `gpt-5.5` |
| `SMTP_SERVER` | SMTP 服务器 | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` | SMTP 用户名 | `your_email@gmail.com` |
| `SMTP_PASSWORD` | SMTP 密码/应用密码 | `xxxx xxxx xxxx xxxx` |
| `EMAIL_TO` | 收件人地址（支持多收件人逗号分隔） | `guoqunfei@genomics.cn,user2@example.com` |
| `EMAIL_FROM` | 发件人地址 | `your_email@gmail.com` |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API Key（可选） | `...` |
| `GITHUB_TOKEN` | GitHub PAT（用于 Issue 反馈处理） | `ghp_...` |

### 3. 自定义关键词（可选）

编辑 `config/keywords.yaml` 可自定义：

- **`core_keywords`**：核心关键词白名单，标题或摘要匹配 +1 分
- **`high_value_keywords`**：高价值关键词，标题匹配 +3 分
- **`exclude_keywords`**：排除黑名单，出现则直接丢弃
- **`max_email_papers`** / **`min_relevance_score`** / **`lookback_days`**：推送控制参数
- **`sources`**：各文献源的启用开关和参数

### 4. 手动触发测试

1. 进入仓库 **Actions** 标签
2. 选择 **Daily Literature Digest**
3. 点击 **Run workflow → Run workflow**
4. 等待运行完成（约 3-5 分钟）

### 5. 验证邮件

检查收件箱是否收到标题为 `📚 每日文献综述 | YYYY-MM-DD | N 篇高相关文献` 的邮件。

## 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| 每日文献摘要 | UTC 01:07（北京时间 09:07） | 获取、总结、发送邮件 |
| 每周趋势报告 | 每周日 UTC 02:00 | 汇总近7天文献生成趋势报告 |

如需修改时间，编辑 `.github/workflows/` 中对应文件的 `cron` 表达式。

## 邮件交互功能

邮件每篇文献底部有三个交互按钮：

| 按钮 | 操作 | 效果 |
|------|------|------|
| ⭐ 有用 | 点击自动跳转到 GitHub Issue 创建页 | 记录用户兴趣，后续同类文献加分 |
| ⏰ 3天后提醒 | 同上 | 3天后邮件中提醒该文献 |
| 🚫 不再推送 | 同上 | 该文献及同类文献不再推送 |

> 点击按钮会自动创建带 `feedback` 标签的 GitHub Issue，由 Actions 自动处理并关闭。

## 评分过滤机制

```
基础得分:
  核心关键词匹配: +1 分
  核心关键词出现在标题: +2 分（额外）
  高价值关键词出现在标题: +3 分

用户画像加分:
  根据用户历史 STAR 行为，自动提取高频关键词
  匹配用户兴趣关键词时额外加分（最高 +3 分）

过滤规则:
  排除关键词黑名单: 直接丢弃
  最小相关性分数: min_relevance_score（默认 5 分）
  最大邮件数量: max_email_papers（默认 15 篇）
```

## 依赖

- Python 3.12+
- requests >= 2.31.0

## 许可证

MIT
