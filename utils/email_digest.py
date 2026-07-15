"""
Daily Email Digest + Follow-up Reminders
-----------------------------------------
Sends via Resend (https://resend.com) — free tier: 100 emails/day, 3k/month.
Set RESEND_API_KEY in GitHub Actions secrets.

Sends two types of emails:
1. New jobs digest (daily, if new jobs found)
2. Follow-up reminders (applications due for follow-up)
"""

import os
import html as _html
import logging
from typing import List, Dict
from datetime import date

import requests

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL     = os.getenv("DIGEST_FROM_EMAIL", "jobs@jobsearchsystem.app")


def _send_email(to: str, subject: str, html: str) -> bool:
    """Send one email via Resend API. Returns True on success."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.warning("[Digest] RESEND_API_KEY not set, skipping email")
        return False

    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to":   [to],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"[Digest] Email send failed to {to}: {e}")
        return False


def _esc(v) -> str:
    """Escape attacker-controlled scraped strings before they enter email HTML.
    Job titles/companies come from external boards and Gmail alerts."""
    return _html.escape(str(v or ""), quote=True)


def _job_row_html(job: Dict, rank: int) -> str:
    score_pct = int(job.get("match_score", 0) * 100)
    score_color = "#22c55e" if score_pct >= 70 else "#f59e0b" if score_pct >= 40 else "#94a3b8"
    reasons = _esc(", ".join(job.get("match_reasons", []) or []))
    j_title = _esc(job.get("job_title", ""))
    j_company = _esc(job.get("company", ""))
    j_location = _esc(job.get("location", ""))
    j_salary = _esc(job.get("salary_range", "")) if job.get("salary_range") else ""
    # Only allow http(s) job URLs into href — a javascript:/data: or quote-breaking
    # URL from a scraped feed must not become a link/attribute-injection.
    _url = str(job.get("job_url", "") or "")
    j_url = _esc(_url) if _url.startswith("http://") or _url.startswith("https://") else "#"

    return f"""
    <tr>
      <td style="padding:12px 0;border-bottom:1px solid #f1f5f9;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
          <div>
            <a href="{j_url}" style="font-size:15px;font-weight:600;color:#1e293b;text-decoration:none;">
              {j_title}
            </a>
            <div style="color:#475569;font-size:13px;margin-top:4px;">
              {j_company} · {j_location}
              {f" · {j_salary}" if j_salary else ''}
            </div>
            {f'<div style="color:#64748b;font-size:12px;margin-top:2px;">{reasons}</div>' if reasons else ''}
          </div>
          <span style="background:{score_color};color:white;font-size:11px;font-weight:700;
                       padding:2px 8px;border-radius:99px;white-space:nowrap;margin-left:12px;">
            {score_pct}%
          </span>
        </div>
        <div style="margin-top:8px;">
          <a href="{j_url}"
             style="background:#6366f1;color:white;padding:4px 12px;border-radius:6px;
                    font-size:12px;text-decoration:none;font-weight:500;">
            View &amp; Apply →
          </a>
        </div>
      </td>
    </tr>
    """


def send_daily_digest(
    user_email: str,
    user_name: str,
    new_jobs: List[Dict],
    follow_ups: List[Dict],
    stale: List[Dict],
) -> bool:
    """Send daily digest combining new jobs + reminders."""
    if not new_jobs and not follow_ups and not stale:
        # No news = no email. An empty digest trains people to ignore the real ones.
        logger.info(f"[Digest] Nothing to send to {user_email}")
        return True

    today_str = date.today().strftime("%B %d, %Y")
    total_new = len(new_jobs)

    # ── New jobs section ──
    jobs_html = ""
    if new_jobs:
        top_jobs = new_jobs[:10]  # top 10 only — the digest is a shortlist, not a dump
        jobs_rows = "\n".join(_job_row_html(j, i+1) for i, j in enumerate(top_jobs))
        more_str = f"<p style='color:#64748b;font-size:13px;text-align:center;'>+ {total_new - 10} more in your dashboard</p>" if total_new > 10 else ""
        jobs_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0 4px;">
          <tr>
            <td style="text-align:center;padding:10px;background:#f8fafc;border-radius:8px;">
              <span style="font-size:20px;font-weight:700;color:#4f46e5;">{total_new}</span>
              <span style="font-size:12px;color:#64748b;display:block;">new matches</span>
            </td>
            <td style="width:8px;"></td>
            <td style="text-align:center;padding:10px;background:#f8fafc;border-radius:8px;">
              <span style="font-size:20px;font-weight:700;color:#d97706;">{len(follow_ups)}</span>
              <span style="font-size:12px;color:#64748b;display:block;">follow-ups due</span>
            </td>
            <td style="width:8px;"></td>
            <td style="text-align:center;padding:10px;background:#f8fafc;border-radius:8px;">
              <span style="font-size:20px;font-weight:700;color:#dc2626;">{len(stale)}</span>
              <span style="font-size:12px;color:#64748b;display:block;">going stale</span>
            </td>
          </tr>
        </table>
        <h2 style="color:#1e293b;font-size:18px;margin:24px 0 12px;">
          🎯 Today's top {min(total_new, 10)}
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0">
          {jobs_rows}
        </table>
        {more_str}
        """

    # ── Follow-up reminders ──
    followups_html = ""
    if follow_ups:
        followup_rows = ""
        for app in follow_ups:
            followup_rows += f"""
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                <strong>{_esc(app.get('job_title'))}</strong> at {_esc(app.get('company'))}<br>
                <span style="color:#64748b;font-size:12px;">
                  Stage: {app.get('stage')} · Follow-up due: {app.get('follow_up_date')}
                </span>
              </td>
            </tr>
            """
        followups_html = f"""
        <h2 style="color:#1e293b;font-size:18px;margin:24px 0 12px;">
          🔔 {len(follow_ups)} Follow-up{"s" if len(follow_ups)>1 else ""} Due Today
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0">
          {followup_rows}
        </table>
        """

    # ── Stale application warnings ──
    stale_html = ""
    if stale:
        stale_rows = ""
        for app in stale:
            stale_rows += f"""
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
                <strong>{_esc(app.get('job_title'))}</strong> at {_esc(app.get('company'))}<br>
                <span style="color:#f59e0b;font-size:12px;">
                  ⚠️ Stage: {app.get('stage')} · No update in 7+ days
                </span>
              </td>
            </tr>
            """
        stale_html = f"""
        <h2 style="color:#1e293b;font-size:18px;margin:24px 0 12px;">
          ⚠️ {len(stale)} Stale Application{"s" if len(stale)>1 else ""}
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0">
          {stale_rows}
        </table>
        """

    # ── Full email ──
    # NOTE: also fix the NEXT_PUBLIC_APP_URL GitHub Actions secret — it is set to
    # the non-existent `job-search-system.vercel.app`. The live URL has a `-zeta`.
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "https://job-search-system-zeta.vercel.app")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                 background:#f8fafc;margin:0;padding:20px;">
      <div style="max-width:600px;margin:0 auto;background:white;
                  border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">

        <div style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #e2e8f0;">
          <h1 style="color:#1e293b;font-size:22px;margin:0;">
            Job Search Digest
          </h1>
          <p style="color:#64748b;font-size:13px;margin:4px 0 0;">{today_str}</p>
        </div>

        <p style="color:#475569;font-size:14px;">Hi {user_name or 'there'},</p>

        {jobs_html}
        {followups_html}
        {stale_html}

        <div style="margin-top:32px;padding-top:16px;border-top:1px solid #e2e8f0;text-align:center;">
          <a href="{app_url}/dashboard"
             style="background:#6366f1;color:white;padding:10px 24px;
                    border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
            Open Dashboard →
          </a>
        </div>

        <p style="color:#94a3b8;font-size:11px;text-align:center;margin-top:24px;">
          Job Search System · You're receiving this because you're an active user.
        </p>
      </div>
    </body>
    </html>
    """

    new_str = f"{total_new} new job{'s' if total_new != 1 else ''}" if new_jobs else ""
    reminder_str = f"{len(follow_ups)} follow-up{'s' if len(follow_ups) != 1 else ''} due" if follow_ups else ""
    parts = [p for p in [new_str, reminder_str] if p]
    subject = f"[Job Search] {' · '.join(parts)} — {today_str}"

    return _send_email(user_email, subject, html)
