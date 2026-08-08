"""
naver_scraper.py
- Playwright로 네이버 쇼핑 검색페이지 직접 스크래핑
- mallName=쿠팡 / 마켓컬리 필터
- SG 가격 계산 후 엑셀 출력
"""
import json
import os
import re
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "00_System_Rules", "shopee_config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_sg_prices(row, config):
    margin = config["margin"]
    supply_price = float(row.get("supply_price_krw", 0) or 0)
    shopee_fee_ratio = margin.get("shopee_fee_ratio", 0.13)
    margin_ratio = margin.get("target_margin_ratio", 0.30)
    vat_ratio = margin.get("vat_ratio", 0.09)
    exchange_rate = margin.get("exchange_rate_krw", 1000.0)

    shipping_krw = (
        margin.get("domeggeme_shipping_krw", 3000)
        + margin.get("forwarding_fee_krw", 2000)
        + margin.get("handling_fee_krw", 1200)
    )

    denominator = 1.0 - shopee_fee_ratio - margin_ratio
    if denominator <= 0:
        return None

    result = {}
    for qty in [1, 2, 3]:
        total_cost_krw = (supply_price * qty) + shipping_krw
        target_price_krw = total_cost_krw / denominator
        target_price_krw_taxed = target_price_krw * (1.0 + vat_ratio)
        target_price_foreign = target_price_krw_taxed / exchange_rate
        result[f"price_{qty}p_sgd"] = round(target_price_foreign, 2)
        result[f"price_{qty}p_krw"] = round(target_price_krw_taxed, 0)
    return result


def scrape(query="쿠팡", mall_filter=None, max_items=100):
    if mall_filter is None:
        mall_filter = ["쿠팡", "마켓컬리"]

    results = []
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

        # Scroll to load more items
        for i in range(5):
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(1)

        # Parse product cards
        items = []
        try:
            items = page.query_selector_all("div.product_item__kqppK, div.product_item, li.product_item")
        except Exception:
            pass

        if not items:
            try:
                items = page.query_selector_all("[class*='product_item']")
            except Exception:
                items = []

        print(f"[*] Found {len(items)} product cards")

        for el in items[:max_items]:
            try:
                # mall name
                mall_el = el.query_selector("a.product_mall__dZaSj, [class*='mall'], a[class*='mall']")
                mall = mall_el.inner_text().strip() if mall_el else ""
                if not mall:
                    mall_el = el.query_selector("span.product_mall, [class*='mall']")
                    mall = mall_el.inner_text().strip() if mall_el else ""

                if mall not in mall_filter:
                    continue

                # title
                title_el = el.query_selector("a.product_link__CSkzz, a[class*='title'], [class*='title']")
                title = title_el.inner_text().strip() if title_el else ""
                if not title:
                    title_el = el.query_selector("a")
                    title = title_el.inner_text().strip() if title_el else ""

                # price
                price_el = el.query_selector("span.price_num__Mxcoy, span[class*='price'], em.price")
                price_text = price_el.inner_text().strip() if price_el else ""
                price = int(re.sub(r"[^\d]", "", price_text) or 0)

                # image
                img_el = el.query_selector("img.product_img__faKbS, img[class*='img'], img")
                img_url = img_el.get_attribute("src") if img_el else ""
                if not img_url:
                    img_url = img_el.get_attribute("data-src") if img_el else ""

                # link
                link_el = el.query_selector("a.product_link__CSkzz, a[href*='shopping.naver.com']")
                link = link_el.get_attribute("href") if link_el else ""
                if not link and title_el:
                    link = title_el.get_attribute("href") or ""

                results.append({
                    "mall_name": mall,
                    "product_name": title,
                    "supply_price_krw": price,
                    "image_url": img_url,
                    "link": link,
                })
            except Exception:
                continue

        browser.close()
    return results


def run(query="쿠팡"):
    config = load_config()
    mall_filter = [m.strip() for m in config.get("naver", {}).get("mall_name_filter", ["쿠팡", "마켓컬리"]) if m.strip()]
    items = scrape(query=query, mall_filter=mall_filter, max_items=config.get("naver", {}).get("display", 100))
    print(f"[*] Scraped items after filter: {len(items)}")

    rows = []
    for it in items:
        prices = calc_sg_prices(it, config)
        if not prices:
            continue
        row = dict(it)
        row.update(prices)
        rows.append(row)

    df = pd.DataFrame(rows)
    out_dir = os.path.join(os.path.dirname(__file__), "02_Output")
    os.makedirs(out_dir, exist_ok=True)
    today = datetime.today().strftime("%Y-%m-%d")
    path = os.path.join(out_dir, f"Naver_SG_Sourcing_{today}.xlsx")
    df.to_excel(path, index=False)
    print(f"[+] Scraping done: {len(df)} items -> {path}")
    return path


if __name__ == "__main__":
    run()
