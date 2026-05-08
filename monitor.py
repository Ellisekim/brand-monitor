import os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
import csv, os, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

KEYWORDS_FILE = "keywords.txt"
RESULTS_FILE  = "results.csv"
SCREENSHOT_DIR = "screenshots"

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "wldwkd25@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "nhzr rpca bnju paky")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "cuckoo@digitaltrinity.co.kr")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

def load_keywords():
    with open(KEYWORDS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def send_alert(keyword, device, checked_at):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"🚨 [브랜드검색 미노출] {keyword} ({device})"
    body = f"""
브랜드검색 미노출이 감지되었습니다.

키워드: {keyword}
매체: {device}
감지시각: {checked_at}

네이버에서 직접 확인해주세요.
https://search.naver.com/search.naver?query={keyword}
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"  → 알림 메일 발송 완료")
    except Exception as e:
        print(f"  → 메일 발송 실패: {e}")

def check_brand_search(page, keyword, device):
    url = f"https://search.naver.com/search.naver?query={keyword}"
    page.goto(url, wait_until="networkidle")

    selector = ".brand_search, #brand_block, [class*='brand_']"
    exposed =  page.locator(selector).count() > 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    status = "exposed" if exposed else "not_exposed"
    shot_path = f"{SCREENSHOT_DIR}/{keyword}_{device}_{status}_{ts}.png"
    page.screenshot(path=shot_path, full_page=False)

    return exposed, shot_path

def save_result(keyword, device, exposed, shot_path):
    checked_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    status = "노출" if exposed else "미노출"

    write_header = not os.path.exists(RESULTS_FILE)
    with open(RESULTS_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["checked_at", "keyword", "device", "status", "screenshot"])
        writer.writerow([checked_at, keyword, device, status, shot_path])

    print(f"[{checked_at}] [{device}] {keyword} → {status}")

    if not exposed:
        send_alert(keyword, device, checked_at)

def run():
    keywords = load_keywords()
    with sync_playwright() as p:

        # PC 체크
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for keyword in keywords:
            try:
                exposed, shot_path = check_brand_search(page, keyword, "PC")
                save_result(keyword, "PC", exposed, shot_path)
            except Exception as e:
                print(f"[오류][PC] {keyword}: {e}")
        browser.close()

        # MO 체크
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={"width": 390, "height": 844}
        )
        page = context.new_page()
        for keyword in keywords:
            try:
                exposed, shot_path = check_brand_search(page, keyword, "MO")
                save_result(keyword, "MO", exposed, shot_path)
            except Exception as e:
                print(f"[오류][MO] {keyword}: {e}")
        browser.close()

if __name__ == "__main__":
    run()