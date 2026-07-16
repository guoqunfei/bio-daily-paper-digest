#!/usr/bin/env python3
"""
Follow-up Reminder Module - Manage pending paper reminders
待跟进提醒模块：管理用户标记的待精读文献，生成提醒内容
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from scripts.user_preferences import get_preferences


class FollowUpManager:
    """Manage follow-up reminders for papers"""

    def __init__(self):
        self.prefs = get_preferences()

    def get_due_reminders(self) -> List[Dict]:
        """Get all follow-up items that are due today or earlier"""
        return self.prefs.get_due_follow_ups()

    def get_upcoming_reminders(self, days: int = 7) -> List[Dict]:
        """Get follow-up items due within the next N days"""
        today = datetime.now()
        upcoming = []
        for key, item in self.prefs.follow_up.items():
            reminder_date = datetime.strptime(item["reminder_date"], "%Y-%m-%d")
            if (reminder_date - today).days <= days and reminder_date >= today:
                upcoming.append({
                    "key": key,
                    **item,
                    "days_until": (reminder_date - today).days
                })
        return upcoming

    def mark_completed(self, paper_key: str):
        """Mark a follow-up as completed"""
        if paper_key in self.prefs.follow_up:
            del self.prefs.follow_up[paper_key]
            self.prefs._save_json(self.prefs.follow_up_file, self.prefs.follow_up)
            print(f"[FollowUp] Marked as completed: {paper_key}")

    def generate_reminder_section(self) -> str:
        """Generate markdown section for due reminders"""
        due = self.get_due_reminders()
        if not due:
            return ""

        lines = [
            "## ⏰ 待跟进提醒",
            "",
            "您标记为 'follow_up' 的以下文献已到期：",
            "",
        ]

        for i, item in enumerate(due, 1):
            title = item.get("title", "Unknown")[:80]
            url = item.get("url", "")
            reminder_date = item.get("reminder_date", "N/A")
            lines.extend([
                f"{i}. [{title}]({url})",
                f"   - 提醒日期: {reminder_date}",
                "",
            ])

        lines.extend([
            "---",
            "",
        ])

        return "\n".join(lines)

    def generate_email_reminder_html(self) -> str:
        """Generate HTML section for email reminders"""
        due = self.get_due_reminders()
        if not due:
            return ""

        items_html = []
        for item in due:
            title = item.get("title", "Unknown")[:80]
            url = item.get("url", "")
            reminder_date = item.get("reminder_date", "N/A")
            items_html.append(f"""
                <tr>
                    <td style="padding:8px;border-bottom:1px solid #eee;">
                        <a href="{url}" style="color:#2a7ae2;text-decoration:none;font-weight:500;">{title}</a>
                    </td>
                    <td style="padding:8px;border-bottom:1px solid #eee;color:#666;text-align:center;">{reminder_date}</td>
                </tr>
            """)

        return f"""
        <div style="background:#fff3cd;border-left:4px solid #ffc107;padding:15px;margin:20px 0;border-radius:4px;">
            <h3 style="margin-top:0;color:#856404;">⏰ 待跟进提醒</h3>
            <p style="color:#856404;">您标记为 'follow_up' 的以下文献已到期：</p>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <thead>
                    <tr style="background:#f8f9fa;">
                        <th style="padding:8px;text-align:left;border-bottom:2px solid #dee2e6;">文献标题</th>
                        <th style="padding:8px;text-align:center;border-bottom:2px solid #dee2e6;width:120px;">提醒日期</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(items_html)}
                </tbody>
            </table>
        </div>
        """

    def get_stats(self) -> Dict:
        """Get follow-up statistics"""
        total = len(self.prefs.follow_up)
        due = len(self.get_due_reminders())
        upcoming = len(self.get_upcoming_reminders(days=7))
        return {
            "total": total,
            "due_today": due,
            "upcoming_7d": upcoming
        }


def get_follow_up_manager() -> FollowUpManager:
    """Factory function"""
    return FollowUpManager()
