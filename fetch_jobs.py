#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TK Job Digest – Daily GitHub Automation
Fetches Data Analyst, Intern, and Graduate Trainee roles targeting Nigeria.
Sends results via SendGrid Email, Telegram, and WhatsApp (Twilio).
"""

import os, re, datetime, pytz, requests
from bs4 import BeautifulSoup

APP_NAME = "TK Job Digest"
MAX_JOBS = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
WAT = pytz.timezone("Africa/Lagos")

# ========== HELPERS ==========
def now_wat():
    return datetime.datetime.now(WAT).strftime("%Y-%m-%d %H:%M")

def clean_text(s):
    return re.sub(r"\s+", " ", s or "").strip()

def infer_role_type(title):
    t = title.lower()
    if "graduate" in t and "trainee" in t:
        return "Graduate Trainee"
    if "intern" in t:
        return "Intern"
    if "analyst" in t:
        return "Data Analyst"
    return "Other"

def infer_remote_or_onsite(title, location):
    t = (title + " " + (location or "")).lower()
    if any(word in t for word in ["remote", "hybrid", "home"]):
        return "Remote"
    return "Onsite"

def policy_ok(role, type_):
    if role in ["Data Analyst", "Intern"] and type_ == "Remote":
        return True
    if role == "Graduate Trainee" and type_ == "Onsite":
        return True
    return False

# ========== SCRAPERS ==========
def scrape_myjobmag():
    url = "https://www.myjobmag.com/search/jobs?q=Data+Analyst"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href*='/job/']"):
            title = clean_text(a.text)
            if "analyst" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "—",
                    "location": "Nigeria",
                    "source": "MyJobMag",
                    "link": requests.compat.urljoin(url, a.get("href"))
                })
    except Exception as e:
        print("MyJobMag:", e)
    return jobs

def scrape_indeed():
    url = "https://ng.indeed.com/jobs?q=Data+Analyst&l=Nigeria"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for c in soup.select("a.tapItem"):
            title = clean_text(c.select_one("h2 span").text if c.select_one("h2 span") else "")
            if "analyst" in title.lower():
                jobs.append({
                    "title": title,
                    "company": clean_text(c.select_one(".companyName").text if c.select_one(".companyName") else "—"),
                    "location": clean_text(c.select_one(".companyLocation").text if c.select_one(".companyLocation") else "Nigeria"),
                    "source": "Indeed",
                    "link": requests.compat.urljoin("https://ng.indeed.com", c.get("href"))
                })
    except Exception as e:
        print("Indeed:", e)
    return jobs

def scrape_jobberman():
    url = "https://www.jobberman.com/jobs?q=Data+Analyst"
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for c in soup.select("a[href^='/job/']"):
            title = clean_text(c.text)
            if "analyst" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "—",
                    "location": "Nigeria",
                    "source": "Jobberman",
                    "link": requests.compat.urljoin("https://www.jobberman.com", c.get("href"))
                })
    except Exception as e:
        print("Jobberman:", e)
    return jobs

# ========== COMBINE + FILTER ==========
def combine_jobs():
    jobs = scrape_myjobmag() + scrape_indeed() + scrape_jobberman()
    uniq, results = set(), []
    for j in jobs:
        key = (j["title"].lower(), j["link"])
        if key in uniq:
            continue
        uniq.add(key)
        role = infer_role_type(j["title"])
        worktype = infer_remote_or_onsite(j["title"], j["location"])
        if not policy_ok(role, worktype):
            continue
        j["role_type"] = role
        j["worktype"] = worktype
        results.append(j)
    return results[:MAX_JOBS]

# ========== FORMATTERS ==========
def to_html(jobs):
    logo = "https://raw.githubusercontent.com/AdoTk1/TK_digest/main/assets/tk_logo.png"
    if not jobs:
        return f"""
        <div style='font-family:Arial;padding:20px;'>
          <img src='{logo}' style='width:100%;max-width:600px;border-radius:8px;'>
          <h2>{APP_NAME}</h2><p>No new jobs found today.</p>
          <p style='color:#777;'>Generated {now_wat()} WAT</p>
        </div>
        """
    rows = "".join([
        f"<tr><td>{j['title']}</td><td>{j['company']}</td><td>{j['location']}</td>"
        f"<td>{j['role_type']}</td><td>{j['worktype']}</td>"
        f"<td><a href='{j['link']}'>Apply</a></td><td>{j['source']}</td></tr>"
        for j in jobs
    ])
    return f"""
    <div style='font-family:Arial;background:#f8f9fa;'>
      <div style='max-width:900px;margin:auto;background:#fff;border-radius:10px;'>
        <img src='{logo}' style='width:100%;border-radius:10px 10px 0 0;'>
        <div style='padding:20px;'>
          <h2>💼 {APP_NAME}</h2>
          <p>Data Analyst & Intern roles ({len(jobs)} found) — {now_wat()} WAT</p>
          <table style='width:100%;border-collapse:collapse;'>
            <tr><th>Title</th><th>Company</th><th>Location</th><th>Role</th><th>Type</th><th>Apply</th><th>Source</th></tr>
            {rows}
          </table>
          <p style='color:#aaa;font-size:12px;text-align:center;'>Generated automatically at 7:00 AM WAT</p>
        </div>
      </div>
    </div>"""

def to_text(jobs):
    if not jobs:
        return f"{APP_NAME}: No jobs found ({now_wat()} WAT)"
    lines = [f"🔥 {APP_NAME} — {now_wat()} WAT"]
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['title']} • {j['company']} • {j['location']} • {j['role_type']} ({j['worktype']})\n{j['link']}")
    return "\n\n".join(lines)

# ========== SENDING ==========
def send_email_sendgrid(html_body):
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To

    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = os.environ.get("EMAIL_TO")
    if not api_key or not to_email:
        print("⚠️ Missing SENDGRID_API_KEY or EMAIL_TO, skipping email send.")
        return

    message = Mail(
        from_email=Email("adotanko01@gmail.com", "TK Job Digest"),
        to_emails=To(to_email),
        subject=f"📊 {APP_NAME} — {now_wat()} WAT",
        html_content=html_body
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print("✅ Email sent! Status:", response.status_code)
    except Exception as e:
        print("❌ SendGrid Error:", e)

def send_telegram(text):
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Telegram not configured.")
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True})
    print("📨 Telegram:", r.status_code)

def send_whatsapp(text):
    from twilio.rest import Client
    sid, token = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")
    w_from, w_to = os.environ.get("TWILIO_WHATSAPP_FROM"), os.environ.get("WHATSAPP_TO")
    if not all([sid, token, w_from, w_to]):
        print("⚠️ WhatsApp not configured.")
        return
    try:
        msg = Client(sid, token).messages.create(from_=w_from, to=w_to, body=text)
        print("✅ WhatsApp message SID:", msg.sid)
    except Exception as e:
        print("❌ WhatsApp Error:", e)

# ========== MAIN ==========
def main():
    jobs = combine_jobs()
    html, text = to_html(jobs), to_text(jobs)

    send_email_sendgrid(html)
    send_telegram(text)
    send_whatsapp(text)

    print(f"✅ Finished: {len(jobs)} jobs sent ({now_wat()} WAT)")

if __name__ == "__main__":
    main()
