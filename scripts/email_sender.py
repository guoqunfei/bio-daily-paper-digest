#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送模块：Table 布局兼容 QQ/Gmail/Outlook + 纯文本 fallback + 多收件人 + 交互链接
"""

import os
import smtplib
import ssl
import traceback
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict


class EmailSender:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "").strip()
        port_str = os.environ.get("SMTP_PORT", "587").strip()
        self.smtp_port = int(port_str) if port_str else 587
        self.smtp_user = os.environ.get("SMTP_USER", "").strip()
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
        email_to_raw = os.environ.get("EMAIL_TO", "").strip()
        self.email_to = [e.strip() for e in email_to_raw.split(",") if e.strip()]
        self.email_from = os.environ.get("EMAIL_FROM", self.smtp_user).strip()
        self.repo_owner = os.environ.get("REPO_OWNER", "guoqunfei")
        self.repo_name = os.environ.get("REPO_NAME", "bio-daily-paper-digest")
        print("[EMAIL] ===== EmailSender Config =====")
        print(f"[EMAIL] Server:   {self.smtp_server}:{self.smtp_port}")
        print(f"[EMAIL] User:     {self.smtp_user}")
        print(f"[EMAIL] From:     {self.email_from}")
        print(f"[EMAIL] To:       {self.email_to}")
        print(f"[EMAIL] Password: {'已设置 (length=' + str(len(self.smtp_password)) + ')' if self.smtp_password else '未设置'}")
        print("[EMAIL] =================================")

    def send_digest(self, papers: List[Dict], digest_md: str, due_reminders: List[Dict] = None) -> bool:
        missing = []
        if not self.smtp_server:
            missing.append("SMTP_SERVER")
        if not self.smtp_user:
            missing.append("SMTP_USER")
        if not self.smtp_password:
            missing.append("SMTP_PASSWORD")
        if not self.email_to:
            missing.append("EMAIL_TO")
        if missing:
            print(f"[EMAIL] ❌ SKIP: Missing env vars: {missing}")
            return False

        subject = f"📚 每日文献综述 | {datetime.now().strftime('%Y-%m-%d')} | {len(papers)} 篇高相关文献"
        try:
            html_body = self._build_html_email(papers, digest_md, due_reminders)
        except Exception as e:
            print(f"[EMAIL] ❌ Failed to build HTML: {e}")
            traceback.print_exc()
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.email_to)

        plain_text = self._build_plain_text(papers, digest_md, due_reminders)
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        print(f"[EMAIL] Connecting to {self.smtp_server}:{self.smtp_port}...")
        server = None
        try:
            if self.smtp_port == 465:
                print("[EMAIL] Using SMTP_SSL (port 465)")
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30, context=context)
            else:
                print(f"[EMAIL] Using SMTP + STARTTLS (port {self.smtp_port})")
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                server.starttls(context=ssl.create_default_context())
            print("[EMAIL] TLS established")
            server.login(self.smtp_user, self.smtp_password)
            print("[EMAIL] ✅ Login successful")
            server.sendmail(self.email_from, self.email_to, msg.as_string())
            server.quit()
            print(f"[EMAIL] ✅ Sent to {', '.join(self.email_to)}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            print(f"[EMAIL] ❌ AUTH FAILED: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            print(f"[EMAIL] ❌ CONNECTION FAILED: {e}")
            return False
        except Exception as e:
            print(f"[EMAIL] ❌ ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    def _build_plain_text(self, papers: List[Dict], digest_md: str, due_reminders: List[Dict] = None) -> str:
        lines = [
            "🧬 基因组学与结构变异 · 每日文献推送",
            f"日期: {datetime.now().strftime('%Y-%m-%d')} | 共 {len(papers)} 篇高相关文献",
            "=" * 50,
            ""
        ]
        if due_reminders:
            lines.append("⏰ 待跟进提醒（您3天前标记）：")
            for fu in due_reminders[:5]:
                lines.append(f"  - {fu.get('paper_title', fu['paper_key'])[:60]}... ({fu.get('created_at', '')[:10]})")
            lines.append("")
        for i, p in enumerate(papers[:15], 1):
            s = p.get("summary", {}) if isinstance(p.get("summary"), dict) else {}
            lines.append(f"{i}. [{p.get('source', 'N/A')}] {p.get('title', 'Untitled')}")
            lines.append(f"   链接: {p.get('url', '#')}")
            lines.append(f"   相关性: {s.get('relevance_score', 0)}/10")
            if s.get("one_sentence"):
                lines.append(f"   总结: {s['one_sentence']}")
            if s.get("action_recommendation"):
                lines.append(f"   建议: {s['action_recommendation']}")
            lines.append("")
        lines.append("---")
        lines.append("由 GitHub Actions 自动生成")
        return "\n".join(lines)

    def _build_interactive_links(self, paper: Dict, user_email: str) -> str:
        paper_key = paper.get("doi", "") or paper.get("arxiv_id", "") or paper.get("pmid", "") or paper.get("title", "")[:50]
        base_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/issues/new"
        def make_link(action: str, label: str, color: str) -> str:
            title = f"[{action}] {paper_key}"
            body = f"""用户: {user_email}
操作: {action}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
文献标题: {paper.get('title', '')}
文献链接: {paper.get('url', '')}

---
> 点击 Submit new issue 即可完成标记。无需修改任何内容。
"""
            params = {"title": title, "body": body, "labels": "feedback"}
            query = urllib.parse.urlencode(params)
            url = f"{base_url}?{query}"
            return f'<a href="{url}" style="display:inline-block; background-color:{color}; color:white; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-family:Arial,Helvetica,sans-serif; margin-right:6px;">{label}</a>'
        links = [
            make_link("STAR", "⭐ 有用", "#2563eb"),
            make_link("FOLLOW_UP", "⏰ 3天后提醒", "#d97706"),
            make_link("IGNORE", "🚫 不再推送", "#6b7280"),
        ]
        return f'<div style="margin-top:10px;">{"".join(links)}</div>'

    def _build_html_email(self, papers: List[Dict], digest_md: str, due_reminders: List[Dict] = None) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        header_html = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#1e3a5f; padding:24px 20px; border-radius:8px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="color:#ffffff; font-size:20px; font-weight:bold; font-family:Arial,Helvetica,sans-serif; line-height:1.4;">🧬 基因组学与结构变异 · 每日文献推送</td></tr><tr><td height="8"></td></tr><tr><td style="color:#bfdbfe; font-size:13px; font-family:Arial,Helvetica,sans-serif; line-height:1.5;">结构变异检测 | 基因组组装 | 节肢动物/猪基因组 | 抗冻蛋白 | Hi-C/三维基因组 | 长读长测序</td></tr><tr><td height="4"></td></tr><tr><td style="color:#93c5fd; font-size:12px; font-family:Arial,Helvetica,sans-serif;">📅 {today} · 来源: PubMed / arXiv / Semantic Scholar · 共 {len(papers)} 篇高相关文献</td></tr></table></td></tr></table>'
        stats_html = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#fff7ed; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:4px;"><span style="color:#92400e; font-size:13px; font-family:Arial,Helvetica,sans-serif;"><strong>📊 今日统计</strong> &nbsp;共获取 <strong>{len(papers)}</strong> 篇高相关性文献，已按分数降序排列</span></td></tr></table>'

        # 待跟进提醒板块
        reminder_html = ""
        if due_reminders:
            reminder_items = "".join([
                f'<div style="margin-bottom:6px;"><a href="{fu.get("paper_url", "#")}" style="color:#2563eb; text-decoration:none; font-weight:bold;">{fu.get("paper_title", fu["paper_key"])[:60]}...</a> <span style="color:#6b7280; font-size:11px;">(标记于 {fu.get("created_at", "")[:10]})</span></div>'
                for fu in due_reminders[:5]
            ])
            reminder_html = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#fef3c7; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:4px;"><div style="font-size:13px; font-weight:bold; color:#92400e; font-family:Arial,Helvetica,sans-serif; margin-bottom:8px;">⏰ 待跟进提醒（您3天前标记）</div><div style="font-size:12px; color:#78350f; font-family:Arial,Helvetica,sans-serif;">{reminder_items}</div></td></tr></table>'

        papers_html = []
        for i, p in enumerate(papers[:15], 1):
            s = p.get("summary", {}) if isinstance(p.get("summary"), dict) else {}
            title = p.get("title", "Untitled")
            url = p.get("url", "#")
            source = p.get("source", "N/A")
            journal = p.get("journal", "N/A")
            authors = p.get("authors", "N/A")
            date = p.get("date", "N/A")
            doi = p.get("doi", "")
            one = s.get("one_sentence", "")
            rel = s.get("relevance_score", 0)
            innov = s.get("method_innovation", "")
            metrics = s.get("key_metrics", "")
            code = s.get("code_repo", "")
            action = s.get("action_recommendation", "")

            src_colors = {"pubmed": ("#dbeafe", "#1e40af"), "arxiv": ("#f3e8ff", "#6b21a8"), "semantic": ("#fce7f3", "#9d174d")}
            src_key = source.lower().split()[0] if source else ""
            src_bg, src_color = src_colors.get(src_key, ("#f3f4f6", "#374151"))
            src_label = {"pubmed": "PubMed", "arxiv": "arXiv", "semantic": "Semantic"}.get(src_key, source)

            if rel >= 8:
                rel_bg, rel_color, rel_border = "#d1fae5", "#059669", "#a7f3d0"
            elif rel >= 5:
                rel_bg, rel_color, rel_border = "#fef3c7", "#d97706", "#fde68a"
            else:
                rel_bg, rel_color, rel_border = "#f3f4f6", "#6b7280", "#e5e7eb"

            if code and "github" in code.lower():
                code_html = f'<a href="{code}" style="color:#2563eb; text-decoration:none; font-weight:bold;">🔗 {code}</a> <span style="color:#059669; font-size:12px;">✅ 可复现</span>'
            elif code and code not in ("未提供", "信息不足", ""):
                code_html = f'<span style="color:#6b7280;">{code}</span> <span style="color:#d97706; font-size:12px;">⚠️ 受限</span>'
            else:
                code_html = '<span style="color:#9ca3af; font-size:13px;">❌ 未提供代码仓库</span>'

            title_link = f'<a href="{url}" style="color:#1e40af; text-decoration:none; font-weight:bold; font-size:15px; line-height:1.4;">{title}</a>' if url != "#" else f'<span style="color:#1f2937; font-weight:bold; font-size:15px; line-height:1.4;">{title}</span>'

            fields = ""
            if one:
                fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px; color:#6b7280; font-weight:bold; font-family:Arial,Helvetica,sans-serif; text-transform:uppercase; letter-spacing:0.5px;">💡 一句话总结</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px; color:#374151; line-height:1.6; font-family:Arial,Helvetica,sans-serif;">{one}</td></tr>'
            if innov:
                fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px; color:#6b7280; font-weight:bold; font-family:Arial,Helvetica,sans-serif; text-transform:uppercase; letter-spacing:0.5px;">🔧 方法创新</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px; color:#374151; line-height:1.6; font-family:Arial,Helvetica,sans-serif;">{innov}</td></tr>'
            if metrics:
                fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px; color:#6b7280; font-weight:bold; font-family:Arial,Helvetica,sans-serif; text-transform:uppercase; letter-spacing:0.5px;">📊 核心指标</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px; color:#374151; line-height:1.6; font-family:Arial,Helvetica,sans-serif;">{metrics}</td></tr>'
            if action:
                fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px; color:#6b7280; font-weight:bold; font-family:Arial,Helvetica,sans-serif; text-transform:uppercase; letter-spacing:0.5px;">🎯 推荐操作</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px; color:#2563eb; line-height:1.6; font-family:Arial,Helvetica,sans-serif; font-weight:600;">{action}</td></tr>'

            # 交互链接
            interactive = self._build_interactive_links(p, self.email_to[0] if self.email_to else "unknown")

            paper_card = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#ffffff; border:1px solid #e5e7eb; border-radius:8px; padding:16px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="1%" style="white-space:nowrap; padding-right:8px;"><span style="display:inline-block; background-color:{src_bg}; color:{src_color}; font-size:10px; font-weight:bold; padding:2px 8px; border-radius:4px; font-family:Arial,Helvetica,sans-serif;">{src_label}</span></td><td style="vertical-align:top;">{title_link}</td><td width="1%" style="white-space:nowrap; padding-left:8px;"><span style="display:inline-block; background-color:{rel_bg}; color:{rel_color}; font-size:12px; font-weight:bold; padding:3px 8px; border-radius:4px; border:1px solid {rel_border}; font-family:Arial,Helvetica,sans-serif;">相关性 {rel}/10</span></td></tr></table></td></tr><tr><td height="8"></td></tr><tr><td style="font-size:12px; color:#6b7280; font-family:Arial,Helvetica,sans-serif;">📰 {journal} &nbsp;|&nbsp; 👤 {authors} &nbsp;|&nbsp; 📆 {date} {" &nbsp;|&nbsp; 🔗 " + doi if doi else ""}</td></tr>{fields}<tr><td height="8"></td></tr><tr><td style="font-size:11px; color:#6b7280; font-weight:bold; font-family:Arial,Helvetica,sans-serif; text-transform:uppercase; letter-spacing:0.5px;">💻 代码仓库</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px; font-family:Arial,Helvetica,sans-serif;">{code_html}</td></tr><tr><td height="8"></td></tr><tr><td>{interactive}</td></tr></table></td></tr></table>'
            papers_html.append(paper_card)

        if not papers:
            papers_html.append('<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="text-align:center; padding:40px; color:#6b7280; font-family:Arial,Helvetica,sans-serif; font-size:14px;">今日无高相关性新文献（或全部被过滤）</td></tr></table>')

        footer = '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;"><tr><td style="background-color:#ffffff; border:1px solid #e5e7eb; border-radius:8px; padding:16px; text-align:center;"><span style="font-size:12px; color:#6b7280; font-family:Arial,Helvetica,sans-serif;">此邮件由 GitHub Actions 自动生成 · <a href="https://github.com/guoqunfei/bio-daily-paper-digest" style="color:#2563eb; text-decoration:none;">查看仓库</a></span></td></tr></table>'

        return f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>每日文献综述</title></head><body style="margin:0; padding:20px; background-color:#f5f7fa; font-family:Arial,Helvetica,sans-serif;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center"><table width="800" cellpadding="0" cellspacing="0" border="0" style="max-width:800px;">{header_html}{stats_html}{reminder_html}{"".join(papers_html)}{footer}</table></td></tr></table></body></html>'


if __name__ == "__main__":
    import sys
    print("EmailSender module loaded. Run via main.py")
