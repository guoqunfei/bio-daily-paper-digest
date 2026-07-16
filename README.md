# Bio Daily Paper Digest v6

> 自动化每日文献综述推送系统 v6 —— 全功能版：三源抓取 + LLM 智能摘要 + 趋势分析 + GitHub 反馈 + Cloudflare Worker

[![Daily Literature Digest](https://github.com/guoqunfei/bio-daily-paper-digest/actions/workflows/daily-digest.yml/badge.svg)](https://github.com/guoqunfei/bio-daily-paper-digest/actions/workflows/daily-digest.yml)
[![Weekly Trend Report](https://github.com/guoqunfei/bio-daily-paper-digest/actions/workflows/weekly-trend.yml/badge.svg)](https://github.com/guoqunfei/bio-daily-paper-digest/actions/workflows/weekly-trend.yml)

---

## 目录

- [项目简介](#项目简介)
- [核心功能](#核心功能)
- [v6 扩展功能](#v6-扩展功能)
- [仓库结构](#仓库结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [GitHub Actions 工作流](#github-actions-工作流)
- [Cloudflare Worker](#cloudflare-worker)
- [邮件推送机制](#邮件推送机制)
- [常见问题排查](#常见问题排查)
- [技术栈](#技术栈)
- [致谢](#致谢)

---

## 项目简介

**Bio Daily Paper Digest v6** 是一个面向生命科学领域的全功能自动化文献监控与智能推送系统。

**核心能力：**
- **三源聚合**：arXiv + PubMed + bioRxiv 每日自动抓取
- **LLM 智能摘要**：OpenAI 兼容 API 生成一句话论文总结 + 领域趋势综述
- **多维度去重**：标题哈希 / DOI 精确匹配 / 相似度模糊匹配
- **来源分类统计**：自动分析各数据源占比、识别交叉文献
- **周趋势报告**：每周一自动生成深度领域趋势分析报告
- **GitHub Issue 反馈**：自动提交运行状态报告（成功/失败）
- **Cloudflare Worker**：无服务器 Webhook 端点，支持外部触发

本项目基于 [X-PG13/paper-digest](https://github.com/X-PG13/paper-digest) 的核心理念构建。

---

## 核心功能

### 1. 每日自动文献抓取（三源聚合）
- **arXiv**：arXiv API，按提交日期排序
- **PubMed**：NCBI E-utilities（esearch + esummary），支持 API Key 加速
- **bioRxiv**：bioRxiv API，7 天滚动窗口，关键词过滤
- **增量更新**：仅抓取自上次运行以来的新增文献

### 2. LLM 智能综述生成
- **单篇摘要**：对 Top 15 篇论文自动生成一句话核心贡献总结
- **趋势综述**：基于当日全部文献，LLM 自动生成研究领域趋势分析
- **周深度报告**：每周生成 500 字以内的深度趋势分析
- **多服务商兼容**：OpenAI / Azure / Moonshot / 本地 vLLM

### 3. 邮件推送系统
- **HTML 富文本邮件**：响应式设计，支持桌面端和移动端
- **多收件人 + 附件**：支持多个接收邮箱，可附加 Markdown 文件
- **自定义主题**：动态主题（含日期、文献数量、数据源分布）

---

## v6 扩展功能

### 4. 多维度去重引擎 (`scripts/dedup.py`)
- **标题哈希去重**：MD5 归一化后精确匹配
- **DOI 去重**：跨源 DOI 精确匹配
- **相似度去重**：SequenceMatcher 模糊匹配（阈值 0.85）
- **统计报告**：输出去重前后的数量对比

### 5. 来源分类与统计 (`scripts/source_classifier.py`)
- **来源占比分析**：arXiv / PubMed / bioRxiv 各自占比
- **主导来源识别**：自动标记当日主要数据源
- **交叉文献检测**：识别同时出现在多个源的论文

### 6. 趋势分析器 (`scripts/trend_analyzer.py`)
- **关键词频率统计**：自动提取生物信息学关键词，统计出现频率
- **时间分布分析**：按月统计文献发表趋势
- **作者活跃度**：统计高频出现作者
- **新兴主题检测**：基于关键词共现识别新兴研究热点

### 7. 周趋势报告 (`scripts/trend_report.py` + `weekly-trend.yml`)
- **每周一自动运行**：GitHub Actions 定时触发
- **历史数据聚合**：读取过去 7 天的 digest 文件进行综合分析
- **LLM 深度分析**：生成 500 字以内的周趋势深度报告
- **邮件推送**：周报告自动发送至指定邮箱

### 8. GitHub Issue 反馈 (`scripts/github_feedback.py`)
- **成功报告**：每日运行成功后自动提交 Issue，含文献数量、来源分布
- **错误报告**：运行失败时自动提交 Issue，含完整错误信息和堆栈跟踪
- **周报告 Issue**：每周趋势报告自动生成对应的 GitHub Issue
- **标签管理**：自动添加 `automated`、`daily-digest`、`error` 等标签

### 9. Cloudflare Worker (`cloudflare-worker.js`)
- **健康检查端点** (`/health`)：返回服务状态、版本、时间戳
- **触发端点** (`/trigger/daily`)：通过 Webhook 远程触发 GitHub Actions
- **状态查询** (`/status`)：返回可用端点列表
- **Bearer Token 认证**：支持通过环境变量配置访问令牌

---

## 仓库结构

```
bio-daily-paper-digest/
├── .github/
│   └── workflows/
│       ├── daily-digest.yml          # 每日文献推送工作流
│       └── weekly-trend.yml          # 周趋势报告工作流
├── scripts/                          # 核心功能模块
│   ├── __init__.py
│   ├── config.py                     # 统一配置管理（YAML + 环境变量）
│   ├── dedup.py                      # 多维度去重引擎
│   ├── fetch_papers.py               # 三源文献抓取（arXiv + PubMed + bioRxiv）
│   ├── source_classifier.py          # 来源分类与统计
│   ├── summarize.py                  # LLM 智能摘要生成
│   ├── trend_analyzer.py             # 趋势分析器（关键词/时间/作者）
│   ├── trend_report.py               # 周趋势报告生成
│   ├── github_feedback.py            # GitHub Issue 自动反馈
│   └── email_sender.py               # SMTP 邮件发送
├── main.py                           # 主入口（daily / weekly / cloudflare）
├── cloudflare-worker.js              # Cloudflare Worker 无服务器端点
├── config/
│   ├── settings.yaml                 # 主配置文件
│   └── keywords.yaml                 # 独立关键词配置
├── output/                           # 每日综述 + 周报告归档
├── requirements.txt                  # Python 依赖
├── README.md                         # 本文件
└── LICENSE
```

---

## 快速开始

### 前置要求

- GitHub 账号
- SMTP 邮箱（QQ / 163 / Gmail / 企业邮箱）
- （可选）OpenAI API Key 或兼容 LLM 服务
- （可选）Cloudflare 账号（如需部署 Worker）

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将仓库复制到你的 GitHub 账号下。

### 2. 配置 Secrets

进入仓库 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SMTP_SERVER` | SMTP 服务器地址 | `smtp.genomics.cn` |
| `SMTP_PORT` | SMTP 端口 | `25` 或 `465` |
| `SMTP_USER` | 发件邮箱地址 | `guoqunfei@genomics.cn` |
| `SMTP_PASSWORD` | 邮箱密码/授权码 | `your_password` |
| `EMAIL_RECEIVER` | 收件邮箱（可多个，逗号分隔） | `user@example.com` |
| `OPENAI_API_KEY` | LLM API Key | `sk-...` |
| `OPENAI_BASE_URL` | LLM API 基础地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | LLM 模型名称 | `gpt-4o-mini` |
| `NCBI_API_KEY` | NCBI API Key（提高 PubMed 频率） | `...` |
| `GITHUB_TOKEN` | GitHub Token（用于 Issue 反馈） | `ghp_...` |
| `GITHUB_REPO` | 仓库全名 | `guoqunfei/bio-daily-paper-digest` |

### 3. 配置关键词

编辑 `config/keywords.yaml` 添加你关注的领域关键词。

### 4. 手动触发测试

进入 **Actions → Daily Literature Digest → Run workflow**，手动触发一次运行。

### 5. 等待自动推送

配置完成后，系统每日自动运行，并将综述邮件发送至你的邮箱。每周一额外发送周趋势报告。

---

## 配置说明

### 主配置 (`config/settings.yaml`)

```yaml
search:
  sources: [arxiv, pubmed, biorxiv]
  max_results: 15
digest:
  language: zh
  use_llm: true
  llm_max_papers: 15
llm:
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
email:
  subject_template: "[Bio-Digest] {date} Literature Digest ({count} papers)"
github:
  feedback_enabled: true
  create_issues: true
dedup:
  enabled: true
  similarity_threshold: 0.85
```

### 关键词配置 (`config/keywords.yaml`)

独立关键词文件，便于维护。支持基因组学、测序技术、三维基因组、变异检测、单细胞、计算生物学等分类。

---

## GitHub Actions 工作流

### 每日工作流 (`daily-digest.yml`)

- **触发**：每日 UTC 01:00（北京时间 09:00）
- **权限**：`contents: write`（提交结果）、`issues: write`（创建反馈 Issue）
- **步骤**：安装依赖 → 运行 `main.py --mode daily` → 提交结果到 Git

### 周趋势工作流 (`weekly-trend.yml`)

- **触发**：每周一 UTC 02:00（北京时间 10:00）
- **步骤**：安装依赖 → 运行 `main.py --mode weekly` → 提交周报告到 Git

---

## Cloudflare Worker

部署 `cloudflare-worker.js` 到 Cloudflare Workers，获得以下端点：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查，返回服务状态 |
| `/trigger/daily` | POST | 触发 GitHub Actions 每日工作流（需 Bearer Token） |
| `/status` | GET | 查询所有可用端点 |

**环境变量：**
- `GITHUB_TOKEN`：GitHub Personal Access Token
- `GITHUB_REPO`：仓库全名
- `TRIGGER_TOKEN`：（可选）Webhook 访问令牌

---

## 邮件推送机制

### 每日邮件内容
- 头部：日期、文献总数、数据源分布
- LLM 研究趋势综述（如启用）
- Top 15 论文：每篇含 LLM 一句话摘要
- 页脚：仓库链接

### 周报告邮件内容
- 周期：过去 7 天
- LLM 深度趋势分析
- 关键词频率 Top 10
- 数据源分布统计
- 月度时间分布
- 新兴主题检测

---

## 常见问题排查

### Q1: GitHub Actions 403 错误
**解决**：Settings → Actions → General → Workflow permissions → Read and write permissions

### Q2: 运行成功但未收到邮件
**排查**：检查 Actions 日志中的 `[EmailSender]` 输出 → 确认 Secrets → 检查垃圾邮件箱 → 确认 SMTP 配置

### Q3: LLM 摘要未生成
**排查**：确认 `OPENAI_API_KEY` → 检查 `[LLM]` 日志 → 确认 `OPENAI_BASE_URL` 和 `OPENAI_MODEL` → 未配置时自动降级为原始摘要

### Q4: GitHub Issue 未创建
**排查**：确认 `GITHUB_TOKEN` 有 `issues: write` 权限 → 确认 `GITHUB_REPO` 格式正确 → 检查 Actions 日志中的 `[GitHubFeedback]`

### Q5: 如何切换 LLM 服务商

| 服务商 | OPENAI_BASE_URL | OPENAI_MODEL |
|--------|-----------------|-------------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Azure | `https://your-resource.openai.azure.com/openai/deployments/your-deployment` | `gpt-4` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| vLLM | `http://localhost:8000/v1` | `your-model` |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 自动化调度 | GitHub Actions (`schedule` + `workflow_dispatch`) |
| 文献抓取 | Python `requests` + arXiv API / NCBI E-utilities / bioRxiv API |
| 智能摘要 | OpenAI API / 兼容 API |
| 去重引擎 | MD5 哈希 + SequenceMatcher 相似度 |
| 趋势分析 | 关键词频率 + 共现检测 + 时间序列 |
| 邮件推送 | Python `smtplib` + `email.mime` |
| GitHub 反馈 | GitHub REST API (`requests`) |
| 边缘端点 | Cloudflare Worker (JavaScript) |
| 配置管理 | YAML + 环境变量三级覆盖 |

---

## 致谢

本项目基于 [X-PG13/paper-digest](https://github.com/X-PG13/paper-digest) 的核心理念构建。感谢原作者提供的优秀基础架构。

---

## 许可证

[MIT License](LICENSE)

---

<p align="center">
  <sub>Built with love for the bioinformatics community</sub>
</p>