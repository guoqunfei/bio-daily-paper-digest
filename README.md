# 🧬 Bio Daily Paper Digest

每日自动获取、归纳、总结生命科学领域（基因组学、结构变异等）最新文献，并通过邮件推送。支持每周趋势分析和 GitHub Issue 自动反馈。

## 功能特性

- **多源文献获取**：PubMed / arXiv / Semantic Scholar
- **LLM 智能总结**：使用 gpt-5.5 进行结构化分析
- **HTML 邮件推送**：精美的邮件模板，支持移动端
- **关键词外部配置**：通过 `config/keywords.yaml` 灵活配置监控领域
- **智能去重**：基于 DOI 和标题相似度的去重模块
- **每周趋势报告**：每周自动生成文献趋势分析 Markdown 报告
- **GitHub Issue 反馈**：发现高相关度文献时自动创建 Issue 记录
- **GitHub Actions 自动运行**：每日 UTC 01:07（北京时间 09:07）自动执行
- **研究领域聚焦**：结构变异、基因组组装、节肢动物/猪基因组、抗冻蛋白、Hi-C/三维基因组、长读长测序

## 技术架构

```
bio-daily-paper-digest/
├── .github/workflows/
│   ├── daily-literature-digest.yml  # 每日文献摘要工作流
│   └── weekly-trend.yml             # 每周趋势报告工作流
├── config/
│   └── keywords.yaml                # 关键词配置文件（可热更新）
├── scripts/
│   ├── config.py                    # 集中配置管理
│   ├── fetch_papers.py              # 文献获取（PubMed/arXiv/Semantic Scholar）
│   ├── dedup.py                     # 去重逻辑（DOI + 标题相似度）
│   ├── summarize.py                 # LLM 总结（gpt-5.5）
│   ├── email_sender.py              # 邮件发送（HTML 模板）
│   ├── github_feedback.py           # GitHub Issue 自动反馈
│   ├── trend_report.py              # 周趋势报告生成
│   └── main.py                      # 主程序入口
├── output/                          # 每日综述输出目录
├── requirements.txt                 # Python 依赖
└── README.md
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
| `EMAIL_TO` | 收件人地址 | `guoqunfei@genomics.cn` |
| `EMAIL_FROM` | 发件人地址 | `your_email@gmail.com` |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API Key（可选） | `...` |

### 3. 自定义关键词（可选）

编辑 `config/keywords.yaml` 可自定义监控的研究领域和关键词，无需修改代码即可生效。

### 4. 手动触发测试

1. 进入仓库 **Actions** 标签
2. 选择 **Daily Literature Digest**
3. 点击 **Run workflow → Run workflow**
4. 等待运行完成（约 3-5 分钟）

### 5. 验证邮件

检查收件箱是否收到标题为 `📚 每日文献综述 | YYYY-MM-DD | N 篇新文献` 的邮件。

## 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| 每日文献摘要 | UTC 01:07（北京时间 09:07） | 获取、总结、发送邮件 |
| 每周趋势报告 | 每周日 UTC 02:00 | 汇总近7天文献生成趋势报告 |

如需修改时间，编辑 `.github/workflows/` 中对应文件的 `cron` 表达式。

## 研究领域关键词

通过 `config/keywords.yaml` 配置，当前监控领域：

| 领域 | 关键词 |
|------|--------|
| 结构变异 | structural variation, SV calling, TAD |
| 基因组组装 | genome assembly, chromosome-level, T2T |
| 节肢动物 | Myrmecia, Formicidae, arthropod |
| 猪基因组 | pig genome, Sus scrofa |
| 抗冻蛋白 | antifreeze protein, AFP, ice-binding |
| 测序技术 | Hi-C, long-read, PacBio, Oxford Nanopore |
| 三维基因组 | chromosome conformation, 3D genome |

## 新增功能（v3）

- **🗂️ 关键词外部配置**：研究领域和关键词从代码中抽离到 `config/keywords.yaml`，支持热更新
- **🧹 智能去重**：新增 `dedup.py` 模块，基于 DOI 和标题相似度进行去重
- **📈 每周趋势报告**：新增 `weekly-trend.yml` 工作流和 `trend_report.py`，每周日自动汇总近7天文献生成趋势报告
- **🐛 GitHub Issue 反馈**：新增 `github_feedback.py`，发现高相关度文献时自动创建 GitHub Issue 进行记录和追踪
- **⚙️ 集中配置管理**：新增 `config.py` 统一管理环境变量和配置项

## 依赖

- Python 3.12+
- requests >= 2.31.0

## 许可证

MIT
