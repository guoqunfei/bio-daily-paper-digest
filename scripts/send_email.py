#!/usr/bin/env python3
"""
邮件发送模块：发送 HTML 格式的文献综述邮件
"""

import os
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict


class EmailSender:
    """邮件发送器"""

    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.email_to = os.environ.get("EMAIL_TO", "").split(",")
        self.email_from = os.environ.get("EMAIL_FROM", self.smtp_user)

    def send_digest(self, papers: List[Dict], digest_md: str) -> bool:
        """发送文献综述邮件"""
        try:
            subject = f"📚 每日文献综述 | {datetime.now().strftime('%Y-%m-%d')} | {len(papers)} 篇新文献"
            html_body = self._build_html_email(papers, digest_md)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = ", ".join(self.email_to)

            # 添加 HTML 内容
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            # 发送邮件
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, self.email_to, msg.as_string())

            print(f"[Email] Sent to {', '.join(self.email_to)}")
            return True

        except Exception as e:
            print(f"[Email Error] {e}")
            return False

    def _build_html_email(self, papers: List[Dict], digest_md: str) -> str:
        """构建 HTML 邮件"""
        today = datetime.now().strftime("%Y-%m-%d")

        # 构建文献列表 HTML
        papers_html = []
        for i, p in enumerate(papers[:15], 1):
            summary = p.get("summary", {})
            if isinstance(summary, dict):
                one_sentence = summary.get("one_sentence", "")
                relevance = summary.get("relevance_score", 0)
            else:
                one_sentence = str(summary)[:100] if summary else ""
                relevance = 0

            # 相关性星级
            stars = "⭐" * (relevance // 2) if isinstance(relevance, (int, float)) else ""

            papers_html.append(f"""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 15px; background-color: #fafafa;">
                <div style="font-size: 16px; font-weight: bold; color: #1a237e; margin-bottom: 8px;">
                    {i}. {p['title']}
                </div>
                <div style="font-size: 13px; color: #555; margin-bottom: 5px;">
                    <strong>作者:</strong> {p.get('authors', 'N/A')} | <strong>来源:</strong> {p.get('source', 'N/A')}
                </div>
                <div style="font-size: 13px; color: #555; margin-bottom: 5px;">
                    <strong>日期:</strong> {p.get('date', 'N/A')} | <strong>期刊:</strong> {p.get('journal', 'N/A')}
                </div>
                <div style="font-size: 13px; color: #e65100; margin-bottom: 8px;">
                    <strong>相关性:</strong> {relevance}/10 {stars}
                </div>
                <div style="font-size: 14px; color: #333; line-height: 1.6; margin-bottom: 8px;">
                    {one_sentence}
                </div>
                <div style="font-size: 13px;">
                    <a href="{p.get('url', '#')}" style="color: #1565c0; text-decoration: none;">阅读原文 →</a>
                </div>
            </div>
            """)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>每日文献综述</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px;">
                <h1 style="margin: 0 0 10px 0; font-size: 24px;">🧬 基因组学与结构变异 · 每日文献推送</h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.9;">
                    覆盖领域：结构变异检测 | 基因组组装 | 节肢动物/猪基因组 | 抗冻蛋白 | Hi-C/三维基因组 | 长读长测序
                </p>
                <p style="margin: 10px 0 0 0; font-size: 13px; opacity: 0.8;">
                    来源：PubMed / arXiv / Semantic Scholar | 生成时间：{today}
                </p>
            </div>

            <div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <strong>📊 今日统计</strong><br>
                共获取 <strong>{len(papers)}</strong> 篇新文献
            </div>

            {''.join(papers_html)}

            <div style="margin-top: 30px; padding: 20px; background-color: #f5f5f5; border-radius: 8px; font-size: 12px; color: #666;">
                <p style="margin: 0;">
                    此邮件由 GitHub Actions 自动生成 | 
                    <a href="https://github.com/guoqunfei/bio-daily-paper-digest" style="color: #1565c0;">查看仓库</a>
                </p>
            </div>
        </body>
        </html>
        """
        return html
