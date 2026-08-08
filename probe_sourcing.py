"""
Quick probe: open Coupang/Kurly with the existing chrome_profile persistent context.
Counts card elements and prints title samples.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(r"C:\돈벌ja\Shopee_Factory")
sys.path.insert(0, str(BASE))

URLS = [
    ("coupang", "https://www.coupang.com/np/search?q=%EC%83%9D%EC%88%98&sort=priceAsc"),
    ("kurly", "https://www.kurly.com/search?sword=%EC%83%9D%EC%88%98&sort=price_asc"),
]
SELS = [
    "div.ProductUnit_productUnit__",
    ".button-wrapper",
    "button[class*='button-wrapper']",
    "[class*='button-wrapper']",
    "div[class*='productTitle']",
    "[class*='title']",
    "span.price-number",
    "span[class*='number']",
    "a[href*='/products/']",
]

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=str(BASE / "chrome_profile"),
        channel="chrome",
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        slow_mo=200,
        locale="ko-KR",
    )
    page = ctx.new_page()
    for name, url in URLS:
        print(f"[*] {name}: {url}")
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"    goto failed: {e}")
            continue
        print(f"    title: {page.title()}")
        for sel in SELS:
            try:
                count = page.locator(sel).count()
            except Exception:
                count = -1
            print(f"    {sel}: {count}")
        try:
            print("    sample text:", page.locator("body").first.inner_text(timeout=2000)[:300].replace("\n", " "))
        except Exception as e:
            print("    body read failed:", e)
    ctx.close()
