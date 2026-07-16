# 🧬 Bio Daily Paper Digest

每日自动获取、归纳、总结生命科学领域（基因组学、结构变异等）最新文献，并通过邮件推送。

## 功能特性

- **多源文献获取**：PubMed / arXiv / Semantic Scholar
- **LLM 智能总结**：使用 gpt-5.5 进行结构化分析
- **HTML 邮件推送**：精美的邮件模板，支持移动端
- **GitHub Actions 自动运行**：每日 UTC 01:07（北京时间 09:07）自动执行
- **研究领域聚焦**：结构变异、基因组组装、节肢动物/猪基因组、抗冻蛋白、Hi-C/三维基因组、长读长测序

## 技术架构

```
bio-daily-paper-digest/
├── .github/workflows/
│   └── daily-literature-digest.yml  # GitHub Actions 工作流
├── scripts/
│   ├── fetch_papers.py              # 文献获取（PubMed/arXiv/Semantic Scholar）
│   ├── summarize.py                 # LLM 总结（gpt-5.5）
│   ├── send_email.py                # 邮件发送
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

### 3. 手动触发测试

1. 进入仓库 **Actions** 标签
2. 选择 **Daily Literature Digest**
3. 点击 **Run workflow → Run workflow**
4. 等待运行完成（约 3-5 分钟）

### 4. 验证邮件

检查收件箱是否收到标题为 `📚 每日文献综述 | YYYY-MM-DD | N 篇新文献` 的邮件。

## 定时任务

默认配置：
- **时间**：每天 UTC 01:07（北京时间 09:07）
- **触发器**：`schedule` 和 `workflow_dispatch`

如需修改时间，编辑 `.github/workflows/daily-literature-digest.yml` 中的 `cron` 表达式。

## 研究领域关键词

| 领域 | 关键词 |
|------|--------|
| 结构变异 | structural variation, SV calling, TAD |
| 基因组组装 | genome assembly, chromosome-level, T2T |
| 节肢动物 | Myrmecia, Formicidae, arthropod |
| 猪基因组 | pig genome, Sus scrofa |
| 抗冻蛋白 | antifreeze protein, AFP, ice-binding |
| 测序技术 | Hi-C, long-read, PacBio, Oxford Nanopore |
| 三维基因组 | chromosome conformation, 3D genome |

## 依赖

- Python 3.12+
- requests
- feedparser
- python-dateutil

## 许可证

MIT
