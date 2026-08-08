"""
naver_scraper_debug.py
- 네이버 쇼핑 검색결과 페이지 스크래핑 디버그
- HTML 일부 저장, 후보 셀렉터 카운트 출력
"""
import os
import time

from playwright.sync_api import sync_playwright


def run(query="쿠팡"):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page = context.new_page()
        url = f"https://search.shopping.naver.com/search/all?query={query}&sort=price_asc"
        print(f"[*] Navigating: {url}")
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        for i in range(5):
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(1)

        html = page.content()
        print(f"[*] HTML length: {len(html)}")

        # Save snippet for inspection
        out = os.path.join(os.path.dirname(__file__), "02_Output", f"naver_debug_{query}.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[+] Saved HTML: {out}")

        # candidate selector count
        selectors = [
            "div[class*='product_item']",
            "div[class*='item']",
            "li[class*='item']",
            "[class*='card']",
            "[class*='list'] > li",
            "[class*='product']",
            "div[class*='result']",
        ]
        for sel in selectors:
            try:
                count = page.locator(sel).count()
                print(f"  {sel}: {count}")
            except Exception as e:
                print(f"  {sel}: error {e}")

        # Preview first 1000 chars
        print("\n--- SNIPPET ---")
        print(html[:1400])
        print("--- END SNIPPET ---\n")

        browser.close()


if __name__ == "__main__":
    run()
