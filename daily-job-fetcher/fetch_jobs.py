#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TK Job Digest – Daily GitHub Action
- Scrapes Nigeria-focused Data Analyst / Intern / Graduate Trainee roles
- Applies filters (Remote vs Onsite by role type)
- Sends HTML email (SendGrid), Telegram message, and WhatsApp (Twilio)
"""

import os, re, time, json, math, datetime
from datetime import datetime, timedelta, timezone
import pytz
import requests
from bs4 import BeautifulSoup

# ========= Config =========
APP_NAME = "TK Job Digest"
MAX_JOBS = 15
DAYS_WINDOW = 7  # last 7 days
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

WAT = pytz.timezone("Africa/Lagos")

# ========= Helpers =========
def now_wat_iso():
    return datetime.now(WAT).strftime("%Y-%m-%d %H:%M")

def clean_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def is_recent(date_str):
    # Very heuristic: if sites provide 'days ago' or date strings; accept if blank (we can't tell)
    # If 'today'/'just posted'/'hours ago' or <=7 days, accept.
    s = (date_str or "").lower()
    if any(k in s for k in ["today", "just", "hour"]):
        return True
    m = re.search(r"(\d+)\s+day", s)
    if m:
        return int(m.group(1)) <= DAYS_WINDOW
    m = re.search(r"(\d+)\s+hour", s)
    if m:
        return True
    # ISO-like
    try:
        dt = datetime.fromisoformat(date_str[:10])
        return (datetime.now() - dt).days <= DAYS_WINDOW
    except Exception:
        # If no date info, keep it; sites often omit
        return True

def infer_role_type(title: str):
    t = title.lower()
    if "graduate" in t and "trainee" in t:
        return "Graduate Trainee"
    if "intern" in t or "internship" in t:
        return "Intern"
    if "analyst" in t:
        return "Data Analyst"
    return "Other"

def infer_remote_or_onsite(title, location):
    t = (title + " " + (location or "")).lower()
    if "remote" in t or "hybrid" in t or "work from home" in t:
        return "Remote"
    return "Onsite"

def passes_policy(role_type, remote_onsite):
    # Policy: Analyst + Intern => Remote; Graduate Trainee => Onsite
    if role_type in ["Data Analyst", "Intern"]:
        return remote_onsite == "Remote"
    if role_type == "Graduate Trainee":
        return remote_onsite == "Onsite"
    return False

def normalize_url(base, href):
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        # take domain from base
        from urllib.parse import urlparse, urljoin
        return urljoin(base, href)
    # else maybe relative
    from urllib.parse import urljoin
    return urljoin(base, href)

# ========= Scrapers =========
def scrape_myjobmag():
    url = "https://www.myjobmag.com/search/jobs?q=Data+Analyst"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        # Cards under .job-list or search results
        cards = soup.select(".job-list li, .job-list .jobs-list, .job-card, .job-listing")
        if not cards:
            cards = soup.select("a.job-listing, a[href*='/job/']")
        for c in cards:
            title_el = c.select_one("a")
            title = clean_space(title_el.get_text()) if title_el else ""
            link = normalize_url(url, title_el.get("href") if title_el else "")
            comp = clean_space((c.select_one(".company, .job-company") or {}).get_text() if c.select_one(".company, .job-company") else "")
            loc = clean_space((c.select_one(".location") or {}).get_text() if c.select_one(".location") else "")
            date_text = clean_space((c.select_one(".job-date, .date") or {}).get_text() if c.select_one(".job-date, .date") else "")
            if title and "analyst" in title.lower():
                jobs.append({
                    "title": title, "company": comp or "—", "location": loc or "Nigeria",
                    "date": date_text, "source": "MyJobMag", "link": link
                })
    except Exception as e:
        print("MyJobMag error:", e)
    return jobs

def scrape_indeed():
    url = "https://ng.indeed.com/jobs?q=Data+Analyst&l=Nigeria"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a.tapItem")
        for c in cards:
            title = clean_space(c.select_one("h2 span") .get_text() if c.select_one("h2 span") else "")
            link = normalize_url("https://ng.indeed.com", c.get("href"))
            comp = clean_space((c.select_one(".companyName") or {}).get_text() if c.select_one(".companyName") else "")
            loc = clean_space((c.select_one(".companyLocation") or {}).get_text() if c.select_one(".companyLocation") else "Nigeria")
            date_text = clean_space((c.select_one(".date") or {}).get_text() if c.select_one(".date") else "")
            if "analyst" in title.lower():
                jobs.append({
                    "title": title, "company": comp or "—", "location": loc,
                    "date": date_text, "source": "Indeed", "link": link
                })
    except Exception as e:
        print("Indeed error:", e)
    return jobs

def scrape_jobberman():
    url = "https://www.jobberman.com/jobs?q=Data+Analyst"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href^='/job/'], a[href*='/job/']")
        for c in cards:
            title = clean_space(c.get_text())
            link = normalize_url("https://www.jobberman.com", c.get("href"))
            # Try to find nearby company/location info
            parent = c.find_parent()
            comp = ""
            loc = "Nigeria"
            if parent:
                comp_el = parent.find(string=re.compile("(?i)company|employer"))
            jobs.append({
                "title": title, "company": comp or "—", "location": loc,
                "date": "", "source": "Jobberman", "link": link
            })
    except Exception as e:
        print("Jobberman error:", e)
    return jobs

def merge_and_filter(all_lists):
    # Combine
    items = []
    seen = set()
    for lst in all_lists:
        for j in lst:
            key = (j["title"].lower(), j["link"])
            if key in seen:
                continue
            seen.add(key)
            role_type = infer_role_type(j["title"])
            remote_onsite = infer_remote_or_onsite(j["title"], j.get("location",""))
            if not passes_policy(role_type, remote_onsite):
                continue
            if not is_recent(j.get("date","")):
                continue
            items.append({
                **j,
                "role_type": role_type,
                "remote_onsite": remote_onsite
            })
    # Prefer most informative (with date)
    return items[:MAX_JOBS]

# ========= Formatters =========
def to_html_email(jobs):
    if not jobs:
        return f"""
        <div style="font-family:Inter,Arial,sans-serif;padding:16px;">
          <img src="cid:tk_logo.png" alt="TK Job Digest" style="max-width:100%;height:auto;border-radius:8px;" />
          <h2>🔥 {APP_NAME}</h2>
          <p>No matching roles found today. Check again tomorrow.</p>
          <p style="color:#888;">Generated {now_wat_iso()} WAT</p>
        </div>
        """
    rows = []
    for j in jobs:
        rows.append(f"""
        <tr>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;"><b>{j['title']}</b><br/><span style="color:#666;">{j['company']}</span></td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{j['location']}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{j['remote_onsite']}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{j['role_type']}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;"><a href="{j['link']}">Apply</a></td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{j.get('source','')}</td>
        </tr>
        """)
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;padding:0;margin:0;background:#f7f9fc;">
      <div style="max-width:900px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.06)">
        <img src="cid:tk_logo.png" alt="TK Job Digest" style="width:100%;height:auto;display:block;" />
        <div style="padding:20px 24px;">
          <h2 style="margin:0 0 8px;color:#1f2d5a;">🔥 {APP_NAME}</h2>
          <p style="margin:0 0 16px;color:#475569;">Top opportunities for Data Analysts in Nigeria — {now_wat_iso()} WAT</p>
          <table role="table" style="width:100%;border-collapse:collapse;">
            <thead>
              <tr>
                <th align="left" style="padding:8px 6px;border-bottom:2px solid #e2e8f0;">Role</th>
                <th align="left" style="padding:8px 6px;border-bottom:2px solid #e2e8f0;">Company</th>
                <th align="left" style="padding:8px 6px;border-bottom:2px solid #e2e8f0;">Location</th>
                <th align="left" style="padding:8px 6px;border-bottom:2px solid #e2e8f0;">Type</th>
                <th align="left" style="padding:8px 6px;border-bottom:2px solid #e2e8f0;">Apply</th>
                <th align="left" style="padding:8px 6px;border-bottom:2px solid #e2e8f0;">Source</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <p style="color:#94a3b8;font-size:12px;margin-top:16px;">Generated automatically at 7:00 AM WAT • {APP_NAME}</p>
        </div>
      </div>
    </div>
    """
    return html

def to_text_for_messaging(jobs):
    if not jobs:
        return f"{APP_NAME}: No matching roles today. ({now_wat_iso()} WAT)"
    lines = [f"🔥 {APP_NAME} — {now_wat_iso()} WAT"]
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['title']} • {j['company']} • {j['location']} • {j['role_type']} • {j['remote_onsite']}\n{j['link']}")
    return "\n\n".join(lines)

# ========= Senders =========
def send_email_sendgrid(html_body):
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("EMAIL_TO")
    if not api_key or not to_email:
        print("SendGrid not configured, skipping email.")
        return
    import base64
    import mimetypes
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, Disposition, FileContent, FileType, FileName, Header, Cid

    message = Mail(
        from_email=("no-reply@tk-job-digest.local", "TK Job Digest"),
        to_emails=[To(to_email)],
        subject=f"💼 Daily Data Analyst Job Digest — {datetime.now(WAT).strftime('%b %d %Y')}",
        html_content=html_body
    )

    # Embed logo via Content-ID
    logo_path = os.path.join("assets", "tk_logo.png")
    with open(logo_path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()
    attachment = Attachment()
    attachment.file_content = FileContent(encoded)
    attachment.file_type = FileType("image/png")
    attachment.file_name = FileName("tk_logo.png")
    attachment.disposition = Disposition("inline")
    attachment.content_id = Cid("tk_logo.png")
    message.attachment = attachment

    sg = SendGridAPIClient(api_key)
    resp = sg.send(message)
    print("Email status:", resp.status_code)

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured, skipping.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    r = requests.post(url, data=payload, timeout=30)
    print("Telegram status:", r.status_code)

def send_whatsapp(text):
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    w_from = os.environ.get("TWILIO_WHATSAPP_FROM")
    w_to = os.environ.get("WHATSAPP_TO")
    if not all([sid, token, w_from, w_to]):
        print("Twilio WhatsApp not configured, skipping.")
        return
    from twilio.rest import Client
    client = Client(sid, token)
    msg = client.messages.create(from_=w_from, to=w_to, body=text)
    print("WhatsApp SID:", msg.sid)

# ========= Orchestrator =========
def fetch_all_jobs():
    all_jobs = []
    all_jobs += scrape_myjobmag()
    all_jobs += scrape_indeed()
    all_jobs += scrape_jobberman()
    # Merge + filter
    merged = merge_and_filter([all_jobs])
    return merged

def main(run_once=False):
    jobs = fetch_all_jobs()
    html_body = to_html_email(jobs)
    text_body = to_text_for_messaging(jobs)

    # Send
    send_email_sendgrid(html_body)
    send_telegram(text_body)
    send_whatsapp(text_body)

    print(f"Done at {now_wat_iso()} WAT. Jobs sent: {len(jobs)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once locally, do not loop/schedule")
    args = parser.parse_args()
    main(run_once=args.once)
