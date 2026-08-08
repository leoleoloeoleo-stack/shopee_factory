"""
coupang_debug.py
- 쿠팡 검색결과 HTML 저장 + 후보 셀렉터 카운트
"""
import os
import time
from playwright.sync_api import sync_playwright


def get_chrome_context(pw):
    user_data = os.path.join(os.path.dirname(__file__), "chrome_profile")
    try:
        return pw.chromium.launch_persistent_context(
            user_data_dir=user_data,
            channel="chrome",
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            slow_mo=300,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
    except Exception:
        return pw.chromium.launch(headless=False)


def run():
    with sync_playwright() as pw:
        ctx = get_chrome_context(pw)
        page = ctx.new_page()
        url = "https://www.coupang.com/np/search?q=생수&sort=priceAsc"
        print(f"[*] Navigating: {url}")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(5)
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(1)

        html = page.content()
        print(f"[*] HTML length: {len(html)}")
        out = os.path.join(os.path.dirname(__file__), "02_Output", "coupang_debug.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[+] Saved: {out}")

        selectors = [
            "li.search-product",
            "div[class*='product']",
            "li[class*='product']",
            "div[class*='item']",
            "li[class*='item']",
            "[class*='card']",
            "[class*='goods']",
            "[class*='product-list']",
            "div.search-content",
            "ul.search-product-list",
        ]
        for sel in selectors:
            try:
                count = page.locator(sel).count()
                print(f"  {sel}: {count}")
            except Exception as e:
                print(f"  {sel}: error {e}")

        print("\n--- SNIPPET ---")
        print(html[:1200])
        print("--- END ---\n")
        ctx.close()


if __name__ == "__main__":
    run()
