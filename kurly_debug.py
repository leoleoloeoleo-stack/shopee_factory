"""
kurly_debug.py
- Kurly 검색결과 디버그: HTML 저장 + 후보 셀렉터 카운트
"""
import os
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(__file__)
OUT = os.path.join(BASE, "02_Output")
os.makedirs(OUT, exist_ok=True)

KEYWORDS = ["생수", "음료", "과자"]

SELECTORS = [
    "div[class*='ProductCard']",
    "div[class*='product']",
    "div[class*='Item']",
    "a[href*='/products/']",
    "[class*='name']",
    "[class*='price']",
    "[class*='sales']",
    "del",
    "span[class*='number']",
    "div[class*='card']",
]


def main():
    with sync_playwright() as pw:
        ctx = pw.chromium.launch(headless=True)
        page = ctx.new_page()
        for kw in KEYWORDS:
            url = f"https://www.kurly.com/search?sword={kw}&sort=price_asc"
            print(f"[*] Kurly {kw}: {url}")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[!] goto failed: {e}")
                continue
            time.sleep(2)
            html = page.content()
            path = os.path.join(OUT, f"kurly_debug_{kw}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"    saved {path} size={len(html)}")
            for sel in SELECTORS:
                try:
                    count = page.locator(sel).count()
                except Exception:
                    count = -1
                if count:
                    print(f"    {sel}: {count}")
        ctx.close()


if __name__ == "__main__":
    import time
    main()
