#!/usr/bin/env python3
"""
Email Sender Module - Send HTML digest via SMTP
邮件发送模块：精美的响应式 HTML 邮件模板
"""

import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List


class EmailSender:
    """SMTP email sender with beautiful HTML templates"""

    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "25"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        # 兼容两种变量名
        receivers_str = os.environ.get("EMAIL_TO", "") or os.environ.get("EMAIL_RECEIVER", "")
        self.receivers = [r.strip() for r in receivers_str.split(",") if r.strip()]

    def _md_to_html(self, md_content: str) -> str:
        """Convert markdown digest to structured HTML"""
        lines = md_content.split("\n")
        html_parts = []
        in_overview = False
        in_paper = False
        paper_sections = []
        current_section = []
        overview_text = ""
        title = ""
        date_str = ""
        total_papers = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract title and metadata from first h1
            if line.startswith("# ") and "Digest" in line:
                title = line.replace("# ", "").strip()
                # Extract date from title
                match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
                if match:
                    date_str = match.group(1)
                continue

            # Extract total papers from quote block
            if line.startswith("> **Total Papers:**"):
                total_match = re.search(r'\*\*Total Papers:\*\* (\d+)', line)
                if total_match:
                    total_papers = total_match.group(1)
                sources_match = re.search(r'\*\*Sources:\*\* (.+)', line)
                if sources_match:
                    sources = sources_match.group(1)
                continue

            # Research Trend Overview
            if line == "## Research Trend Overview":
                in_overview = True
                continue
            if in_overview and line.startswith("## ") and "Research Trend" not in line:
                in_overview = False
            if in_overview and line and not line.startswith("---"):
                overview_text += line + " "
                continue

            # Individual papers
            if line.startswith("## ") and ". " in line[:10]:
                if current_section:
                    paper_sections.append(current_section)
                current_section = [line]
                in_paper = True
                continue
            if in_paper:
                if line.startswith("---"):
                    continue
                current_section.append(line)

        if current_section:
            paper_sections.append(current_section)

        return self._build_html_template(date_str, total_papers, overview_text, paper_sections)

    def _build_html_template(self, date_str: str, total_papers: str, overview: str, papers: List[List[str]]) -> str:
        """Build beautiful HTML email template"""

        # Build overview section
        overview_html = ""
        if overview.strip():
            overview_html = f"""
            <div class="overview-card">
                <div class="overview-header">📊 研究趋势综述</div>
                <div class="overview-body">{overview.strip()}</div>
            </div>
            """

        # Build paper cards
        papers_html = ""
        for i, paper_lines in enumerate(papers[:20], 1):  # Limit to 20 papers
            if not paper_lines:
                continue

            # Parse paper info
            title = ""
            source = ""
            published = ""
            authors = ""
            url = ""
            summary = ""
            in_summary = False

            for line in paper_lines:
                if line.startswith("## "):
                    title = line.replace("## ", "").strip()
                    # Remove numbering like "1. "
                    title = re.sub(r'^\d+\.\s*', '', title)
                elif line.startswith("- **Source:**"):
                    parts = line.replace("- **Source:**", "").split("|")
                    source = parts[0].strip() if parts else ""
                    if len(parts) > 1:
                        published = parts[1].replace("**Published:**", "").strip()
                elif line.startswith("- **Authors:**"):
                    authors = line.replace("- **Authors:**", "").strip()
                elif line.startswith("- **URL:**"):
                    url = line.replace("- **URL:**", "").strip()
                elif line == "### Summary":
                    in_summary = True
                    continue
                elif in_summary and line and not line.startswith("---"):
                    summary += line + " "

            source_badge = f'<span class="badge badge-{source.lower().replace(" ", "-")}">{source}</span>' if source else ""

            papers_html += f"""
            <div class="paper-card">
                <div class="paper-header">
                    <div class="paper-number">{i}</div>
                    <div class="paper-title">
                        <a href="{url}" target="_blank">{title}</a>
                    </div>
                </div>
                <div class="paper-meta">
                    {source_badge}
                    <span class="paper-date">📅 {published}</span>
                </div>
                <div class="paper-authors">👤 {authors}</div>
                <div class="paper-summary">{summary.strip()}</div>
            </div>
            """

        # Full HTML template
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bio Daily Paper Digest</title>
<style>
/* Reset */
body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}

/* Base */
body {{
    margin: 0 !important;
    padding: 0 !important;
    background-color: #f4f6f8;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
}}

/* Container */
.container {{
    max-width: 680px;
    margin: 0 auto;
    background-color: #ffffff;
}}

/* Header */
.header {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 30px 40px;
    text-align: center;
}}
.header-title {{
    color: #ffffff;
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 8px 0;
    letter-spacing: 0.5px;
}}
.header-subtitle {{
    color: rgba(255,255,255,0.85);
    font-size: 13px;
    margin: 0;
}}
.header-meta {{
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid rgba(255,255,255,0.2);
    color: rgba(255,255,255,0.9);
    font-size: 12px;
}}

/* Content */
.content {{
    padding: 30px 40px;
}}

/* Overview Card */
.overview-card {{
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    border-left: 4px solid #667eea;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}}
.overview-header {{
    font-size: 15px;
    font-weight: 600;
    color: #667eea;
    margin-bottom: 10px;
}}
.overview-body {{
    font-size: 14px;
    color: #555;
    line-height: 1.7;
}}

/* Paper Card */
.paper-card {{
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
    transition: box-shadow 0.2s;
}}
.paper-card:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}}
.paper-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
}}
.paper-number {{
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    flex-shrink: 0;
    margin-top: 2px;
}}
.paper-title {{
    font-size: 15px;
    font-weight: 600;
    line-height: 1.5;
    flex: 1;
}}
.paper-title a {{
    color: #2c3e50;
    text-decoration: none;
}}
.paper-title a:hover {{
    color: #667eea;
    text-decoration: underline;
}}
.paper-meta {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    margin-left: 40px;
}}
.badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}}
.badge-arxiv {{ background: #e3f2fd; color: #1976d2; }}
.badge-pubmed {{ background: #e8f5e9; color: #388e3c; }}
.badge-biorxiv {{ background: #fff3e0; color: #f57c00; }}
.paper-date {{
    font-size: 12px;
    color: #999;
}}
.paper-authors {{
    font-size: 12px;
    color: #888;
    margin-left: 40px;
    margin-bottom: 10px;
    line-height: 1.5;
}}
.paper-summary {{
    font-size: 13px;
    color: #555;
    line-height: 1.7;
    margin-left: 40px;
    padding-top: 10px;
    border-top: 1px dashed #eee;
}}

/* Footer */
.footer {{
    background: #f8f9fa;
    padding: 25px 40px;
    text-align: center;
    border-top: 1px solid #e8e8e8;
}}
.footer-text {{
    font-size: 12px;
    color: #999;
    margin: 0 0 8px 0;
}}
.footer-link {{
    font-size: 12px;
    color: #667eea;
    text-decoration: none;
}}

/* Mobile */
@media only screen and (max-width: 600px) {{
    .header, .content, .footer {{ padding: 20px !important; }}
    .paper-header {{ flex-direction: column; gap: 8px; }}
    .paper-meta, .paper-authors, .paper-summary {{ margin-left: 0 !important; }}
    .paper-number {{ margin-top: 0; }}
}}
</style>
</head>
<body>
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
    <tr>
        <td align="center" style="background-color: #f4f6f8; padding: 20px 0;">
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <div class="header-title">📚 Bio Daily Paper Digest</div>
                    <div class="header-subtitle">每日生命科学文献智能综述</div>
                    <div class="header-meta">{date_str} | 共 {total_papers} 篇文献</div>
                </div>

                <!-- Content -->
                <div class="content">
                    {overview_html}
                    <div style="font-size: 15px; font-weight: 600; color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea;">
                        📑 文献列表
                    </div>
                    {papers_html}
                </div>

                <!-- Footer -->
                <div class="footer">
                    <p class="footer-text">本邮件由 Bio Daily Paper Digest 自动生成</p>
                    <a class="footer-link" href="https://github.com/guoqunfei/bio-daily-paper-digest">查看仓库</a>
                </div>
            </div>
        </td>
    </tr>
</table>
</body>
</html>"""

    def send_digest(self, digest_path: str, paper_count: int) -> bool:
        """Send digest email with beautiful HTML template"""
        # Skip if SMTP not configured
        if not all([self.smtp_server, self.smtp_user, self.smtp_password]):
            print("[EmailSender] SMTP not configured. Skipping email.")
            return False

        if not self.receivers:
            print("[EmailSender] No receivers configured. Skipping email.")
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"[Bio-Digest] {today} 文献综述 ({paper_count}篇)"

        with open(digest_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        html_body = self._md_to_html(md_content)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(self.receivers)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, self.receivers, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, self.receivers, msg.as_string())
            print(f"[EmailSender] Sent successfully to: {', '.join(self.receivers)}")
            return True
        except Exception as e:
            print(f"[EmailSender] Failed to send email: {e}")
            return False


def get_sender() -> EmailSender:
    return EmailSender()
