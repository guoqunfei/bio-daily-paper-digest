#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送模块：
- 按来源分组（预印本/顶刊/专业期刊）
- 支持 Cloudflare Worker 零操作反馈 + GitHub Issue fallback
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

from source_classifier import SourceClassifier


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

        # 反馈模式：worker = 零操作，issue = GitHub Issue fallback
        self.feedback_mode = os.environ.get("FEEDBACK_MODE", "issue").strip().lower()
        self.worker_url = os.environ.get("FEEDBACK_WORKER_URL", "").strip()
        self.repo_owner = os.environ.get("REPO_OWNER", "guoqunfei")
        self.repo_name = os.environ.get("REPO_NAME", "bio-daily-paper-digest")

        print("[EMAIL] ===== EmailSender Config =====")
        print(f"[EMAIL] Server:   {self.smtp_server}:{self.smtp_port}")
        print(f"[EMAIL] From:     {self.email_from}")
        print(f"[EMAIL] To:       {self.email_to}")
        print(f"[EMAIL] Feedback: {self.feedback_mode} (Worker: {self.worker_url or 'N/A'})")
        print("[EMAIL] =================================")

    def send_digest(self, papers: List[Dict], digest_md: str, due_reminders: List[Dict] = None, 
                    trend_report_md: str = "", personal_todo_md: str = "") -> bool:
        missing = []
        if not self.smtp_server: missing.append("SMTP_SERVER")
        if not self.smtp_user: missing.append("SMTP_USER")
        if not self.smtp_password: missing.append("SMTP_PASSWORD")
        if not self.email_to: missing.append("EMAIL_TO")
        if missing:
            print(f"[EMAIL] ❌ SKIP: Missing {missing}")
            return False

        subject = f"📚 每日文献综述 | {datetime.now().strftime('%Y-%m-%d')} | {len(papers)} 篇"
        try:
            html_body = self._build_html_email(papers, due_reminders, trend_report_md, personal_todo_md)
        except Exception as e:
            print(f"[EMAIL] ❌ HTML build failed: {e}")
            traceback.print_exc()
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.email_to)

        plain = self._build_plain_text(papers, due_reminders, trend_report_md, personal_todo_md)
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        print(f"[EMAIL] Connecting to {self.smtp_server}:{self.smtp_port}...")
        server = None
        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                server.starttls(context=ssl.create_default_context())
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())
            server.quit()
            print(f"[EMAIL] ✅ Sent to {', '.join(self.email_to)}")
            return True
        except Exception as e:
            print(f"[EMAIL] ❌ {type(e).__name__}: {e}")
            return False
        finally:
            if server:
                try: server.close()
                except: pass

    def _build_interactive_links(self, paper: Dict, user_email: str) -> str:
        paper_key = paper.get("doi", "") or paper.get("arxiv_id", "") or paper.get("pmid", "") or paper.get("title", "")[:50]

        if self.feedback_mode == "worker" and self.worker_url:
            # Cloudflare Worker 零操作模式
            base = self.worker_url.rstrip("/")
            def w_link(action, label, color):
                url = f"{base}/?action={action}&paper={urllib.parse.quote(paper_key)}&user={urllib.parse.quote(user_email)}"
                return f'<a href="{url}" style="display:inline-block;background:{color};color:white;text-decoration:none;padding:4px 10px;border-radius:4px;font-size:11px;font-family:Arial;margin-right:6px;">{label}</a>'
            return f'<div style="margin-top:10px;">{w_link("star","⭐ 有用","#2563eb")}{w_link("follow_up","⏰ 3天后提醒","#d97706")}{w_link("ignore","🚫 不再推送","#6b7280")}</div>'
        else:
            # GitHub Issue fallback 模式
            base_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/issues/new"
            def g_link(action, label, color):
                title = f"[{action.upper()}] {paper_key}"
                body = f"""用户: {user_email}
操作: {action}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
文献标题: {paper.get('title', '')}
文献链接: {paper.get('url', '')}

---
> 点击 Submit new issue 完成标记（已预填内容，无需修改）
"""
                params = {"title": title, "body": body, "labels": "feedback"}
                url = f"{base_url}?{urllib.parse.urlencode(params)}"
                return f'<a href="{url}" style="display:inline-block;background:{color};color:white;text-decoration:none;padding:4px 10px;border-radius:4px;font-size:11px;font-family:Arial;margin-right:6px;">{label}</a>'
            return f'<div style="margin-top:10px;">{g_link("star","⭐ 有用","#2563eb")}{g_link("follow_up","⏰ 3天后提醒","#d97706")}{g_link("ignore","🚫 不再推送","#6b7280")}</div>'

    def _build_html_email(self, papers: List[Dict], due_reminders: List[Dict], 
                          trend_report_md: str, personal_todo_md: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")

        # 头部
        header = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#1e3a5f;padding:24px 20px;border-radius:8px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="color:#fff;font-size:20px;font-weight:bold;font-family:Arial;line-height:1.4;">🧬 基因组学与结构变异 · 每日文献推送</td></tr><tr><td height="8"></td></tr><tr><td style="color:#bfdbfe;font-size:13px;font-family:Arial;line-height:1.5;">结构变异检测 | 基因组组装 | 节肢动物/猪基因组 | 抗冻蛋白 | Hi-C/三维基因组 | 长读长测序</td></tr><tr><td height="4"></td></tr><tr><td style="color:#93c5fd;font-size:12px;font-family:Arial;">📅 {today} · 来源: PubMed / arXiv / Semantic Scholar · 共 {len(papers)} 篇高相关文献</td></tr></table></td></tr></table>'

        # 统计
        stats = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#fff7ed;border-left:4px solid #f59e0b;padding:12px 16px;border-radius:4px;"><span style="color:#92400e;font-size:13px;font-family:Arial;"><strong>📊 今日统计</strong> &nbsp;共 <strong>{len(papers)}</strong> 篇高相关性文献，已按来源分组</span></td></tr></table>'

        # 待办提醒
        reminder = ""
        if due_reminders:
            items = "".join([f'<div style="margin-bottom:6px;"><a href="{fu.get("paper_url","#")}" style="color:#2563eb;text-decoration:none;font-weight:bold;">{fu.get("paper_title",fu["paper_key"])[:60]}...</a> <span style="color:#6b7280;font-size:11px;">(标记于 {fu.get("created_at","")[:10]})</span></div>' for fu in due_reminders[:5]])
            reminder = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#fef3c7;border-left:4px solid #f59e0b;padding:12px 16px;border-radius:4px;"><div style="font-size:13px;font-weight:bold;color:#92400e;font-family:Arial;margin-bottom:8px;">⏰ 待跟进提醒（您3天前标记）</div><div style="font-size:12px;color:#78350f;font-family:Arial;">{items}</div></td></tr></table>'

        # 按来源分组
        groups = {"preprint": [], "top": [], "method": [], "general": []}
        for p in papers:
            cat = SourceClassifier.classify(p)
            groups[cat].append(p)

        papers_html = []
        for cat in ["preprint", "top", "method", "general"]:
            group = groups[cat]
            if not group:
                continue

            cat_name = SourceClassifier.get_display_name(cat)
            cat_color = {"preprint": "#f3e8ff", "top": "#dbeafe", "method": "#d1fae5", "general": "#f3f4f6"}[cat]
            cat_border = {"preprint": "#6b21a8", "top": "#1e40af", "method": "#059669", "general": "#6b7280"}[cat]

            papers_html.append(f'<tr><td style="padding:8px 0;"><div style="font-size:14px;font-weight:bold;color:{cat_border};font-family:Arial;padding:8px 12px;background:{cat_color};border-radius:6px;border-left:3px solid {cat_border};">{cat_name} · {len(group)} 篇</div></td></tr>')

            for i, p in enumerate(group[:15], 1):
                s = p.get("summary", {}) if isinstance(p.get("summary"), dict) else {}
                title = p.get("title", "Untitled")
                url = p.get("url", "#")
                source = p.get("source", "N/A")
                journal = p.get("journal", "N/A")
                authors = p.get("authors", "N/A")
                date = p.get("date", "N/A")
                doi = p.get("doi", "")
                one = s.get("one_sentence", "")
                rel = min(s.get("relevance_score", 0), 10)
                innov = s.get("method_innovation", "")
                metrics = s.get("key_metrics", "")
                code = s.get("code_repo", "")
                action = s.get("action_recommendation", "")

                src_colors = {"pubmed": ("#dbeafe", "#1e40af"), "arxiv": ("#f3e8ff", "#6b21a8"), "semantic": ("#fce7f3", "#9d174d")}
                src_key = source.lower().split()[0] if source else ""
                src_bg, src_color = src_colors.get(src_key, ("#f3f4f6", "#374151"))
                src_label = {"pubmed": "PubMed", "arxiv": "arXiv", "semantic": "Semantic"}.get(src_key, source)

                if rel >= 8: rel_bg, rel_color, rel_border = "#d1fae5", "#059669", "#a7f3d0"
                elif rel >= 5: rel_bg, rel_color, rel_border = "#fef3c7", "#d97706", "#fde68a"
                else: rel_bg, rel_color, rel_border = "#f3f4f6", "#6b7280", "#e5e7eb"

                if code and "github" in code.lower():
                    code_html = f'<a href="{code}" style="color:#2563eb;text-decoration:none;font-weight:bold;">🔗 {code}</a> <span style="color:#059669;font-size:12px;">✅ 可复现</span>'
                elif code and code not in ("未提供", "信息不足", ""):
                    code_html = f'<span style="color:#6b7280;">{code}</span> <span style="color:#d97706;font-size:12px;">⚠️ 受限</span>'
                else:
                    code_html = '<span style="color:#9ca3af;font-size:13px;">❌ 未提供代码仓库</span>'

                title_link = f'<a href="{url}" style="color:#1e40af;text-decoration:none;font-weight:bold;font-size:15px;line-height:1.4;">{title}</a>' if url != "#" else f'<span style="color:#1f2937;font-weight:bold;font-size:15px;line-height:1.4;">{title}</span>'

                fields = ""
                if one: fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px;color:#6b7280;font-weight:bold;font-family:Arial;text-transform:uppercase;letter-spacing:0.5px;">💡 一句话总结</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px;color:#374151;line-height:1.6;font-family:Arial;">{one}</td></tr>'
                if innov and innov != "信息不足": fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px;color:#6b7280;font-weight:bold;font-family:Arial;text-transform:uppercase;letter-spacing:0.5px;">🔧 方法创新</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px;color:#374151;line-height:1.6;font-family:Arial;">{innov}</td></tr>'
                if metrics and metrics != "信息不足": fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px;color:#6b7280;font-weight:bold;font-family:Arial;text-transform:uppercase;letter-spacing:0.5px;">📊 核心指标</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px;color:#374151;line-height:1.6;font-family:Arial;">{metrics}</td></tr>'
                if action and action != "信息不足": fields += f'<tr><td height="8"></td></tr><tr><td style="font-size:11px;color:#6b7280;font-weight:bold;font-family:Arial;text-transform:uppercase;letter-spacing:0.5px;">🎯 推荐操作</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px;color:#2563eb;line-height:1.6;font-family:Arial;font-weight:600;">{action}</td></tr>'

                interactive = self._build_interactive_links(p, self.email_to[0] if self.email_to else "unknown")

                card = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="1%" style="white-space:nowrap;padding-right:8px;"><span style="display:inline-block;background:{src_bg};color:{src_color};font-size:10px;font-weight:bold;padding:2px 8px;border-radius:4px;font-family:Arial;">{src_label}</span></td><td style="vertical-align:top;">{title_link}</td><td width="1%" style="white-space:nowrap;padding-left:8px;"><span style="display:inline-block;background:{rel_bg};color:{rel_color};font-size:12px;font-weight:bold;padding:3px 8px;border-radius:4px;border:1px solid {rel_border};font-family:Arial;">相关性 {rel}/10</span></td></tr></table></td></tr><tr><td height="8"></td></tr><tr><td style="font-size:12px;color:#6b7280;font-family:Arial;">📰 {journal} &nbsp;|&nbsp; 👤 {authors} &nbsp;|&nbsp; 📆 {date} {" &nbsp;|&nbsp; 🔗 " + doi if doi else ""}</td></tr>{fields}<tr><td height="8"></td></tr><tr><td style="font-size:11px;color:#6b7280;font-weight:bold;font-family:Arial;text-transform:uppercase;letter-spacing:0.5px;">💻 代码仓库</td></tr><tr><td height="4"></td></tr><tr><td style="font-size:13px;font-family:Arial;">{code_html}</td></tr><tr><td height="8"></td></tr><tr><td>{interactive}</td></tr></table></td></tr></table>'
                papers_html.append(f'<tr><td>{card}</td></tr>')

        if not papers_html:
            papers_html.append('<tr><td style="text-align:center;padding:40px;color:#6b7280;font-family:Arial;font-size:14px;">今日无高相关性新文献</td></tr>')

        # 趋势报告（如果有）
        trend_section = ""
        if trend_report_md:
            trend_lines = trend_report_md.split("\n")[:30]  # 只取前30行
            trend_html = "<br>".join(trend_lines).replace("# ", "<strong>").replace("## ", "<strong style='color:#2563eb'>")
            trend_section = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;"><tr><td style="background-color:#f0f9ff;border-left:4px solid #0ea5e9;padding:16px;border-radius:4px;"><div style="font-size:13px;font-weight:bold;color:#0369a1;font-family:Arial;margin-bottom:8px;">📈 近30天趋势速览</div><div style="font-size:12px;color:#075985;font-family:Arial;">{trend_html}</div></td></tr></table>'

        footer = '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;"><tr><td style="background-color:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;text-align:center;"><span style="font-size:12px;color:#6b7280;font-family:Arial;">此邮件由 GitHub Actions 自动生成 · <a href="https://github.com/guoqunfei/bio-daily-paper-digest" style="color:#2563eb;text-decoration:none;">查看仓库</a></span></td></tr></table>'

        return f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>每日文献综述</title></head><body style="margin:0;padding:20px;background-color:#f5f7fa;font-family:Arial,Helvetica,sans-serif;"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center"><table width="800" cellpadding="0" cellspacing="0" border="0" style="max-width:800px;">{header}{stats}{reminder}{trend_section}<tr><td><table width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(papers_html)}</table></td></tr>{footer}</table></td></tr></table></body></html>'

    def _build_plain_text(self, papers: List[Dict], due_reminders: List[Dict], trend_md: str, todo_md: str) -> str:
        lines = ["🧬 基因组学与结构变异 · 每日文献推送", f"日期: {datetime.now().strftime('%Y-%m-%d')} | 共 {len(papers)} 篇", "=" * 50, ""]
        if due_reminders:
            lines.append("⏰ 待跟进提醒：")
            for fu in due_reminders[:5]:
                lines.append(f"  - {fu.get('paper_title', fu['paper_key'])[:60]}... ({fu.get('created_at', '')[:10]})")
            lines.append("")
        if todo_md:
            lines.append(todo_md)
            lines.append("")
        for i, p in enumerate(papers[:15], 1):
            s = p.get("summary", {}) if isinstance(p.get("summary"), dict) else {}
            cat = SourceClassifier.classify(p)
            cat_name = {"preprint": "预印本", "top": "顶刊", "method": "专业期刊", "general": "其他"}.get(cat, "其他")
            lines.append(f"{i}. [{cat_name}][{p.get('source', 'N/A')}] {p.get('title', 'Untitled')}")
            lines.append(f"   链接: {p.get('url', '#')}")
            lines.append(f"   相关性: {min(s.get('relevance_score', 0), 10)}/10")
            if s.get("one_sentence"):
                lines.append(f"   总结: {s['one_sentence']}")
            if s.get("action_recommendation"):
                lines.append(f"   建议: {s['action_recommendation']}")
            lines.append("")
        lines.append("---")
        lines.append("由 GitHub Actions 自动生成")
        return "\n".join(lines)


if __name__ == "__main__":
    print("EmailSender module loaded")
