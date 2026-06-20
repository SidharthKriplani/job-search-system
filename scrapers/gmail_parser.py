"""
Gmail Parser — OAuth-based
---------------------------
Reads the user's Gmail for job alert emails from:
  - naukri.com
  - linkedin.com
  - iimjobs.com
  - indeed.com
  - naukrigulf.com
  - foundit.in (formerly Monster India)
  - timesjobs.com
  - shine.com

User must have:
  1. Connected Gmail via OAuth (tokens stored in Supabase gmail_tokens table)
  2. Set up job alerts on each portal (one-time setup, 15 min)
  3. Created a Gmail filter: FROM (naukri.com OR linkedin.com OR ...) → Label "Job Alerts"

The scraper reads that label's unread emails, parses job listings, marks as read.
"""

import base64
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from email import message_from_bytes
from email.header import decode_header

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

GMAIL_LABEL = "Job Alerts"
MAX_EMAILS  = 50   # per run per user

SENDER_PARSERS = {
    "naukri.com":      "_parse_naukri",
    "linkedin.com":    "_parse_linkedin",
    "iimjobs.com":     "_parse_iimjobs",
    "indeed.com":      "_parse_indeed",
    "naukrigulf.com":  "_parse_naukrigulf",
    "foundit.in":      "_parse_foundit_email",
    "timesjobs.com":   "_parse_timesjobs_email",
    "shine.com":       "_parse_shine_email",
}


# ─── Credentials helper ─────────────────────────────────────────────────────

def _get_credentials(token_row: Dict, client_id: str, client_secret: str) -> Optional[Credentials]:
    """Build Google Credentials from stored token row, refreshing if needed."""
    creds = Credentials(
        token=token_row["access_token"],
        refresh_token=token_row["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f"[Gmail] Token refresh failed: {e}")
            return None
    return creds


# ─── Email body extraction ───────────────────────────────────────────────────

def _get_body(message: Dict) -> str:
    """Extract plain text body from Gmail API message."""
    payload = message.get("payload", {})

    def _decode_part(part: Dict) -> str:
        data = part.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        return ""

    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        return _decode_part(payload)

    if mime_type == "text/html":
        html = _decode_part(payload)
        return re.sub(r"<[^>]+>", " ", html)

    # Multipart — walk parts
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            text = _decode_part(part)
            if text:
                return text
    # Fallback: first HTML part
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html":
            html = _decode_part(part)
            if html:
                return re.sub(r"<[^>]+>", " ", html)
    return ""


def _get_header(message: Dict, name: str) -> str:
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


# ─── Portal-specific parsers ─────────────────────────────────────────────────

def _parse_naukri(body: str, date_str: str) -> List[Dict]:
    """Parse Naukri job alert email body."""
    jobs = []
    # Naukri alert format: "Job Title\nCompany Name\nLocation | Salary | Experience"
    # The URLs follow pattern: /job-listings-...
    url_pattern = re.compile(r'(https?://www\.naukri\.com/job-listings[^\s"<>]+)')
    title_pattern = re.compile(r'([A-Z][^\n]{5,80})\n([A-Z][^\n]{2,60})\n([^\n]{5,100})')

    urls = url_pattern.findall(body)
    blocks = title_pattern.findall(body)

    for i, block in enumerate(blocks[:10]):
        title, company, meta = block
        url = urls[i] if i < len(urls) else "https://www.naukri.com"
        location_match = re.search(r'([A-Za-z, ]+)\|', meta)
        location = location_match.group(1).strip() if location_match else ""
        salary_match = re.search(r'\|\s*([0-9].*?)\s*\|', meta)
        salary = salary_match.group(1).strip() if salary_match else None

        jobs.append({
            "job_title": title.strip(),
            "company":   company.strip(),
            "location":  location,
            "salary_range": salary,
            "job_url":   url,
            "description_snippet": meta[:200],
            "posted_date": date_str,
            "source":    "gmail_naukri",
            "source_job_id": url.split("/")[-1].split("?")[0],
        })
    return jobs


def _parse_linkedin(body: str, date_str: str) -> List[Dict]:
    """Parse LinkedIn job alert email."""
    jobs = []
    url_pattern = re.compile(r'(https?://www\.linkedin\.com/jobs/view/[^\s"<>?]+)')
    # LinkedIn emails have job title followed by company and location on next lines
    block_pattern = re.compile(
        r'([A-Z][^\n]{5,100})\n([A-Z][^\n]{2,80})\n([A-Za-z ,]+)(?:\n|$)',
        re.MULTILINE
    )

    urls  = url_pattern.findall(body)
    blocks = block_pattern.findall(body)

    for i, block in enumerate(blocks[:10]):
        title, company, location = block
        url = urls[i] if i < len(urls) else "https://www.linkedin.com/jobs"
        jobs.append({
            "job_title":   title.strip(),
            "company":     company.strip(),
            "location":    location.strip(),
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_linkedin",
            "source_job_id": re.search(r'/(\d+)/?', url).group(1) if re.search(r'/(\d+)/?', url) else url,
        })
    return jobs


def _parse_iimjobs(body: str, date_str: str) -> List[Dict]:
    """Parse iimjobs alert email."""
    jobs = []
    url_pattern = re.compile(r'(https?://(?:www\.)?iimjobs\.com/j/[^\s"<>]+)')
    title_pattern = re.compile(r'([A-Z][^\n]{5,100})\nby ([A-Z][^\n]{2,80})\n')

    urls   = url_pattern.findall(body)
    blocks = title_pattern.findall(body)

    for i, block in enumerate(blocks[:10]):
        title, company = block
        url = urls[i] if i < len(urls) else "https://www.iimjobs.com"
        jobs.append({
            "job_title":   title.strip(),
            "company":     company.strip(),
            "location":    "",
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_iimjobs",
            "source_job_id": url.split("/")[-1].split("?")[0],
        })
    return jobs


def _parse_indeed(body: str, date_str: str) -> List[Dict]:
    """Parse Indeed India alert email."""
    jobs = []
    url_pattern = re.compile(r'(https?://(?:in\.)?indeed\.com/viewjob[^\s"<>]+)')
    urls = url_pattern.findall(body)
    block_pattern = re.compile(r'([A-Z][^\n]{5,100})\n([A-Z][^\n]{2,80})\n([A-Za-z ,\-]+)')
    blocks = block_pattern.findall(body)

    for i, block in enumerate(blocks[:10]):
        title, company, location = block
        url = urls[i] if i < len(urls) else "https://in.indeed.com"
        jobs.append({
            "job_title":   title.strip(),
            "company":     company.strip(),
            "location":    location.strip(),
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_indeed",
            "source_job_id": re.search(r'jk=([a-f0-9]+)', url).group(1) if re.search(r'jk=([a-f0-9]+)', url) else url,
        })
    return jobs


def _parse_naukrigulf(body: str, date_str: str) -> List[Dict]:
    """Parse NaukriGulf alert email."""
    jobs = []
    url_pattern = re.compile(r'(https?://(?:www\.)?naukrigulf\.com/[^\s"<>]+)')
    urls = url_pattern.findall(body)
    block_pattern = re.compile(r'([A-Z][^\n]{5,100})\n([A-Z][^\n]{2,80})\n([A-Za-z ,\-]+)')
    blocks = block_pattern.findall(body)

    for i, block in enumerate(blocks[:10]):
        title, company, location = block
        url = urls[i] if i < len(urls) else "https://www.naukrigulf.com"
        jobs.append({
            "job_title":   title.strip(),
            "company":     company.strip(),
            "location":    location.strip(),
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_naukrigulf",
            "source_job_id": url.split("/")[-1].split("?")[0],
        })
    return jobs


def _parse_foundit_email(body: str, date_str: str) -> List[Dict]:
    jobs = []
    url_pattern = re.compile(r'(https?://(?:www\.)?foundit\.in/[^\s"<>]+)')
    urls = url_pattern.findall(body)
    for i, url in enumerate(urls[:10]):
        jobs.append({
            "job_title":   f"Job Alert {i+1}",
            "company":     "",
            "location":    "",
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_foundit",
            "source_job_id": url.split("/")[-1].split("?")[0],
        })
    return jobs


def _parse_timesjobs_email(body: str, date_str: str) -> List[Dict]:
    jobs = []
    url_pattern = re.compile(r'(https?://(?:www\.)?timesjobs\.com/[^\s"<>]+)')
    urls = url_pattern.findall(body)
    for i, url in enumerate(urls[:10]):
        jobs.append({
            "job_title":   f"Job Alert {i+1}",
            "company":     "",
            "location":    "",
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_timesjobs",
            "source_job_id": url.split("/")[-1].split("?")[0],
        })
    return jobs


def _parse_shine_email(body: str, date_str: str) -> List[Dict]:
    jobs = []
    url_pattern = re.compile(r'(https?://(?:www\.)?shine\.com/[^\s"<>]+)')
    urls = url_pattern.findall(body)
    for i, url in enumerate(urls[:10]):
        jobs.append({
            "job_title":   f"Job Alert {i+1}",
            "company":     "",
            "location":    "",
            "salary_range": None,
            "job_url":     url,
            "description_snippet": "",
            "posted_date": date_str,
            "source":      "gmail_shine",
            "source_job_id": url.split("/")[-1].split("?")[0],
        })
    return jobs


PARSER_MAP = {
    "naukri.com":     _parse_naukri,
    "linkedin.com":   _parse_linkedin,
    "iimjobs.com":    _parse_iimjobs,
    "indeed.com":     _parse_indeed,
    "naukrigulf.com": _parse_naukrigulf,
    "foundit.in":     _parse_foundit_email,
    "timesjobs.com":  _parse_timesjobs_email,
    "shine.com":      _parse_shine_email,
}


# ─── Main scrape function ────────────────────────────────────────────────────

def scrape(profile: Dict, token_row: Dict, client_id: str, client_secret: str,
           supabase_client=None) -> List[Dict]:
    """
    Reads the user's Gmail 'Job Alerts' label for new job alert emails.
    Returns list of normalised job dicts.

    Args:
        profile:       user_profiles row
        token_row:     gmail_tokens row (access_token, refresh_token, etc.)
        client_id:     Google OAuth client ID
        client_secret: Google OAuth client secret
        supabase_client: optional — used to update refreshed token
    """
    creds = _get_credentials(token_row, client_id, client_secret)
    if not creds:
        return []

    # Persist refreshed token if it changed
    if supabase_client and creds.token != token_row.get("access_token"):
        try:
            supabase_client.table("gmail_tokens").update({
                "access_token": creds.token,
                "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
            }).eq("user_id", profile["user_id"]).execute()
        except Exception as e:
            logger.warning(f"[Gmail] Failed to persist refreshed token: {e}")

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"[Gmail] Could not build Gmail service: {e}")
        return []

    # Find the "Job Alerts" label ID
    try:
        labels = service.users().labels().list(userId="me").execute()
        label_id = next(
            (l["id"] for l in labels.get("labels", []) if l["name"] == GMAIL_LABEL),
            None
        )
        if not label_id:
            logger.warning(f"[Gmail] Label '{GMAIL_LABEL}' not found. Create it in Gmail first.")
            return []
    except HttpError as e:
        logger.error(f"[Gmail] Labels list failed: {e}")
        return []

    # Fetch unread messages with this label
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=[label_id, "UNREAD"],
            maxResults=MAX_EMAILS,
        ).execute()
        message_ids = [m["id"] for m in result.get("messages", [])]
    except HttpError as e:
        logger.error(f"[Gmail] Messages list failed: {e}")
        return []

    all_jobs: List[Dict] = []
    processed_ids: List[str] = []

    for msg_id in message_ids:
        try:
            message = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        except HttpError:
            continue

        sender = _get_header(message, "From")
        date_str = _get_header(message, "Date")
        body = _get_body(message)

        # Determine parser
        parser_fn = None
        for domain, fn in PARSER_MAP.items():
            if domain in sender:
                parser_fn = fn
                break

        if parser_fn:
            try:
                jobs = parser_fn(body, date_str[:10] if date_str else None)
                all_jobs.extend(jobs)
                processed_ids.append(msg_id)
            except Exception as e:
                logger.warning(f"[Gmail] Parse error for message {msg_id}: {e}")

    # Mark processed emails as read
    if processed_ids:
        try:
            service.users().messages().batchModify(
                userId="me",
                body={
                    "ids": processed_ids,
                    "removeLabelIds": ["UNREAD"],
                }
            ).execute()
            logger.info(f"[Gmail] Marked {len(processed_ids)} emails as read")
        except HttpError as e:
            logger.warning(f"[Gmail] Could not mark emails as read: {e}")

    logger.info(f"[Gmail] Total jobs parsed: {len(all_jobs)}")
    return all_jobs
