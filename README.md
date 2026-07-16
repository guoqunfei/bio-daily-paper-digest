# Bio Daily Paper Digest

> 自动化每日文献综述推送系统 —— 基于 GitHub Actions 的无人值守文献监控与邮件通知工具

[![Daily Literature Digest](https://github.com/guoqunfei/bio-daily-paper-digest/actions/workflows/daily-digest.yml/badge.svg)](https://github.com/guoqunfei/bio-daily-paper-digest/actions/workflows/daily-digest.yml)

---

## 目录

- [项目简介](#项目简介)
- [核心功能](#核心功能)
- [仓库结构](#仓库结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [GitHub Actions 工作流](#github-actions-工作流)
- [邮件推送机制](#邮件推送机制)
- [常见问题排查](#常见问题排查)
- [技术栈](#技术栈)
- [致谢](#致谢)

---

## 项目简介

**Bio Daily Paper Digest** 是一个面向生命科学领域的自动化文献监控与推送系统。该系统每日定时从学术数据库（如 arXiv、PubMed）抓取特定领域的最新文献，通过大语言模型生成结构化综述摘要，并以邮件形式推送到用户指定邮箱，实现'无人值守'的每日文献跟踪。

本项目基于 [X-PG13/paper-digest](https://github.com/X-PG13/paper-digest) 的核心理念进行扩展，针对生物信息学与基因组学领域进行了深度定制，支持：

- 多源文献聚合（arXiv、PubMed、bioRxiv）
- 智能摘要生成（基于 LLM 的文献综述）
- 定时邮件推送（每日/每周自定义频率）
- GitHub Actions 全自动托管（零服务器成本）

---

## 核心功能

### 1. 每日自动文献抓取
- **定时触发**：通过 GitHub Actions `schedule` 事件，每日 UTC 时间自动运行
- **多源检索**：支持按关键词、作者、期刊、时间范围等多维度检索
- **去重过滤**：基于 DOI/标题的本地去重，避免重复推送
- **增量更新**：仅抓取自上次运行以来的新增文献

### 2. 智能综述生成
- **LLM 摘要**：利用大语言模型对文献标题、摘要进行结构化总结
- **领域定制**：针对基因组学、结构变异、生物信息学等方向优化提示词
- **多语言支持**：支持生成中文或英文综述内容
- **关键信息提取**：自动提取研究背景、方法、结论、意义

### 3. 邮件推送系统
- **HTML 富文本邮件**：支持格式化排版、链接、表格
- **多收件人支持**：可配置多个接收邮箱
- **自定义主题**：支持动态主题（含日期与文献数量）
- **发送状态日志**：完整记录每次发送的成功/失败状态

### 4. 结果持久化与版本控制
- **每日结果归档**：生成的综述文件自动提交到仓库，形成历史记录
- **Git 历史追踪**：可通过 Git 回溯任意日期的文献汇总
- **Badge 状态展示**：README 顶部显示最近一次运行状态

---

## 仓库结构

```
bio-daily-paper-digest/
├── .github/
│   └── workflows/
│       └── daily-digest.yml          # GitHub Actions 工作流定义
├── src/
│   ├── __init__.py
│   ├── main.py                       # 主程序入口：每日文献综述生成
│   ├── fetch_papers.py               # 文献抓取模块
│   ├── generate_digest.py            # 综述生成模块（LLM 调用）
│   └── send_email.py                 # 邮件发送模块
├── output/                           # 每日生成的综述文件存放目录
│   ├── 2026-07-15_digest.md
│   └── 2026-07-16_digest.md
├── config/
│   └── settings.yaml                 # 配置文件（关键词、邮箱、API Key 等）
├── requirements.txt                  # Python 依赖
├── README.md                         # 本文件
└── LICENSE
```

---

## 快速开始

### 前置要求

- GitHub 账号
- 一个支持 SMTP 的邮箱（推荐 QQ邮箱 / 163邮箱 / Gmail / 企业邮箱）
- （可选）OpenAI API Key 或其他 LLM 服务密钥，用于生成综述

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将仓库复制到你的 GitHub 账号下。

### 2. 配置 Secrets

进入仓库 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SMTP_SERVER` | SMTP 服务器地址 | `smtp.genomics.cn` |
| `SMTP_PORT` | SMTP 端口 | `25` 或 `465` |
| `SMTP_USER` | 发件邮箱地址 | `guoqunfei@genomics.cn` |
| `SMTP_PASSWORD` | 邮箱密码/授权码 | `your_password_or_auth_code` |
| `EMAIL_RECEIVER` | 收件邮箱地址（可多个，逗号分隔） | `user@example.com` |
| `OPENAI_API_KEY` | （可选）LLM API Key | `sk-...` |
| `NCBI_API_KEY` | （可选）NCBI API Key，提高 PubMed 请求频率 | `...` |

### 3. 配置检索关键词

编辑 `config/settings.yaml`：

```yaml
search:
  sources:
    - arxiv
    - pubmed
  keywords:
    - "structural variation"
    - "genome assembly"
    - "long-read sequencing"
    - "Hi-C"
  date_range: "last_7_days"      # 检索时间范围
  max_results: 20                # 每日最大文献数

digest:
  language: "zh"                 # 综述语言：zh 或 en
  style: "academic"              # 综述风格

email:
  subject_template: "[Bio-Digest] {date} 文献综述 ({count}篇)"
  send_time: "09:00"            # 本地时间
```

### 4. 手动触发测试

进入仓库 **Actions → Daily Literature Digest → Run workflow**，手动触发一次运行，验证配置是否正确。

### 5. 等待每日自动推送

配置完成后，系统将按照 `cron` 设定的时间每日自动运行，并将综述邮件发送至你的邮箱。

---

## 配置说明

### GitHub Actions Workflow（`.github/workflows/daily-digest.yml`）

```yaml
name: Daily Literature Digest

on:
  schedule:
    # 每天 UTC 01:00 运行（北京时间 09:00）
    - cron: '0 1 * * *'
  workflow_dispatch:  # 支持手动触发

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run digest
        env:
          SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          EMAIL_RECEIVER: ${{ secrets.EMAIL_RECEIVER }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python src/main.py
      
      - name: Commit results
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add output/
          git commit -m "Update daily digest $(date +%Y-%m-%d)" || echo "No changes"
          git push
```

### 主程序入口（`src/main.py`）

主程序负责协调整个流程：

1. **读取配置**：从 `config/settings.yaml` 加载检索参数
2. **抓取文献**：调用 `fetch_papers.py` 从各数据库获取文献元数据
3. **生成综述**：调用 `generate_digest.py` 使用 LLM 生成结构化摘要
4. **发送邮件**：调用 `send_email.py` 推送 HTML 邮件
5. **归档结果**：将综述文件保存到 `output/` 目录并提交到 Git

```python
#!/usr/bin/env python3
"""
主程序：每日文献综述入口
"""

import os
import sys
from datetime import datetime

from fetch_papers import fetch_all_sources
from generate_digest import generate_daily_digest
from send_email import send_digest_email


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] 开始执行每日文献综述...")
    
    # Step 1: 抓取文献
    papers = fetch_all_sources()
    if not papers:
        print("今日无新文献，跳过发送。")
        return
    
    # Step 2: 生成综述
    digest_path = f"output/{today}_digest.md"
    generate_daily_digest(papers, digest_path)
    
    # Step 3: 发送邮件
    send_digest_email(digest_path, paper_count=len(papers))
    
    print(f"[{today}] 任务完成，共处理 {len(papers)} 篇文献。")


if __name__ == "__main__":
    main()
```

### 邮件发送模块（`src/send_email.py`）

邮件发送模块支持 SMTP 认证、HTML 富文本、多收件人等功能：

```python
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_digest_email(digest_path: str, paper_count: int):
    """发送文献综述邮件"""
    
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ.get("SMTP_PORT", 25))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    receivers = os.environ["EMAIL_RECEIVER"].split(",")
    
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"[Bio-Digest] {today} 文献综述 ({paper_count}篇)"
    
    # 读取综述内容
    with open(digest_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 构建 HTML 邮件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(receivers)
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .paper {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; border-radius: 4px; }}
            .title {{ font-weight: bold; font-size: 1.1em; color: #2c3e50; }}
            .authors {{ color: #7f8c8d; font-size: 0.9em; }}
            .summary {{ margin-top: 10px; text-align: justify; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #95a5a6; font-size: 0.85em; text-align: center; }}
        </style>
    </head>
    <body>
        <h1>每日文献综述</h1>
        <p><strong>日期：</strong>{today} | <strong>文献数：</strong>{paper_count} 篇</p>
        <hr>
        {content}
        <div class="footer">
            <p>本邮件由 Bio Daily Paper Digest 自动生成</p>
            <p><a href="https://github.com/guoqunfei/bio-daily-paper-digest">查看仓库</a></p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    # 发送邮件
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, receivers, msg.as_string())
    
    print(f"邮件已发送至: {', '.join(receivers)}")
```

---

## 邮件推送机制

### 邮件内容格式

每封邮件包含以下结构化内容：

| 模块 | 内容 |
|------|------|
| **头部信息** | 日期、文献总数、检索关键词 |
| **今日精选** | 按相关性排序的 Top 5 文献详细摘要 |
| **完整列表** | 所有文献的标题、作者、期刊、链接、一句话总结 |
| **统计信息** | 各数据库来源分布、研究领域分布 |
| **页脚** | 仓库链接、退订说明 |

### 邮件展示效果

邮件采用响应式 HTML 设计，在桌面端和移动端均有良好的阅读体验：

- **标题**：蓝色边框高亮，突出研究主题
- **摘要**：灰色背景卡片，便于快速浏览
- **链接**：所有文献标题直接链接到原文/PDF
- **标签**：自动标注文献来源（arXiv / PubMed / bioRxiv）

---

## 常见问题排查

### Q1: GitHub Actions 运行失败，显示 403 错误

**原因**：GitHub 默认的 `GITHUB_TOKEN` 权限不足，或仓库 Actions 权限未开启读写。

**解决**：
1. 进入 **Settings → Actions → General**
2. 找到 **Workflow permissions**，选择 **Read and write permissions**
3. 勾选 **Allow GitHub Actions to create and approve pull requests**

### Q2: 运行成功但没有收到邮件

**排查步骤**：
1. 检查 Actions 日志中是否有 `邮件已发送至` 的输出
2. 确认 `EMAIL_RECEIVER` 环境变量配置正确
3. 检查垃圾邮件箱
4. 确认 SMTP 服务器地址和端口正确（企业邮箱通常需要内网 SMTP 或 VPN）
5. 部分邮箱（如 Gmail）需要开启'不够安全的应用访问'或使用应用专用密码

### Q3: 如何修改每日运行时间

修改 `.github/workflows/daily-digest.yml` 中的 `cron` 表达式：

```yaml
# 北京时间每天上午 9:00（UTC 01:00）
- cron: '0 1 * * *'

# 北京时间每天晚上 8:00（UTC 12:00）
- cron: '0 12 * * *'
```

### Q4: 如何添加新的文献数据源

在 `src/fetch_papers.py` 中新增抓取函数，并在 `fetch_all_sources()` 中注册：

```python
SOURCES = {
    "arxiv": fetch_arxiv,
    "pubmed": fetch_pubmed,
    "biorxiv": fetch_biorxiv,  # 新增
}
```

### Q5: 如何调整综述生成风格

编辑 `config/settings.yaml` 中的 `digest.style`：

- `academic`：学术严谨风格，适合研究者
- `brief`：简洁速读风格，适合快速浏览
- `detailed`：详细深度风格，包含方法学评价

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 自动化调度 | GitHub Actions (`schedule` + `workflow_dispatch`) |
| 文献抓取 | Python `requests` + arXiv API / NCBI E-utilities |
| 综述生成 | OpenAI GPT-4 / Claude / 本地 LLM（通过 API） |
| 邮件推送 | Python `smtplib` + `email.mime` |
| 配置管理 | YAML |
| 版本控制 | Git + GitHub |

---

## 致谢

本项目基于 [X-PG13/paper-digest](https://github.com/X-PG13/paper-digest) 的核心理念构建，针对生物信息学领域进行了功能扩展与流程优化。感谢原作者提供的优秀基础架构。

---

## 许可证

[MIT License](LICENSE)

---

<p align="center">
  <sub>Built with love for the bioinformatics community</sub>
</p>