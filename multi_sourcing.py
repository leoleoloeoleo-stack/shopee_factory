"""
multi_sourcing.py
- Coupang direct sourcing
- Kurly search sourcing using debug-verified selectors
- Shopee-ready pricing export
"""
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

BASE = Path(r"C:\돈벌자\Shopee_Factory")
OUT = BASE / "02_Output"
CONFIG = BASE / "00_System_Rules" / "shopee_config.json"


def load_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sourcing(items, mall_name):
    OUT.mkdir(parents=True, exist_ok=True)
    if not items:
        return None
    df = pd.DataFrame(items)
    df["mall_name"] = mall_name
    # normalize columns
    for col in ["product_id", "product_name", "supply_price_krw", "image_url", "link", "price_1p_sgd", "price_1p_krw", "price_2p_sgd", "price_2p_krw", "price_3p_sgd", "price_3p_krw"]:
        if col not in df.columns:
            df[col] = None
    out_path = OUT / f"Naver_SG_Sourcing_{datetime.today().isoformat()}.xlsx"
    df.to_excel(out_path, index=False)
    return out_path


def get_chrome_context(pw):
    user_data = str(BASE / "chrome_profile")
    return pw.chromium.launch_persistent_context(
        user_data_dir=user_data,
        channel="chrome",
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        slow_mo=200,
        viewport={"width": 1280, "height": 900},
        locale="ko-KR",
    )


def try_coupang(page, query):
    url = f"https://www.coupang.com/np/search?q={query}&sort=priceAsc"
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    time.sleep(2)
    cards = page.locator("div.ProductUnit_productUnit__")
    count = cards.count()
    items = []
    for i in range(min(count, 60)):
        card = cards.nth(i)
        try:
            title = card.locator("div[class*='productTitle']").first.inner_text(timeout=1000).strip()
        except Exception:
            title = ""
        if not title:
            try:
                title = card.locator("[class*='title']").first.inner_text(timeout=1000).strip()
            except Exception:
                title = ""
        try:
            link = card.locator("a[href*='/products/']").first.get_attribute("href")
            if link and not link.startswith("http"):
                link = "https://www.coupang.com" + link
        except Exception:
            link = ""
        try:
            price = card.locator("div[class*='price'] strong").first.inner_text(timeout=1000).strip()
        except Exception:
            price = ""
        items.append({
            "product_id": f"coupang_{i}_{query}",
            "product_name": title,
            "supply_price_krw": price,
            "image_url": "",
            "link": link,
            "price_1p_sgd": None,
            "price_1p_krw": None,
            "price_2p_sgd": None,
            "price_2p_krw": None,
            "price_3p_sgd": None,
            "price_3p_krw": None,
        })
    return items


def try_kurly(page, query):
    url = f"https://www.kurly.com/search?sword={query}&sort=price_asc"
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    time.sleep(1)
    cards = page.locator("[class*='button-wrapper']")
    count = cards.count()
    items = []
    for i in range(min(count, 60)):
        card = cards.nth(i)
        title = ""
        price = ""
        try:
            title = card.locator("[class*='name'], a[href*='/products/']").first.inner_text(timeout=1000).strip()
        except Exception:
            pass
        try:
            price = card.locator("[class*='price'] span, .price-number").first.inner_text(timeout=1000).strip()
        except Exception:
            pass
        if title or price:
            items.append({
                "product_id": f"kurly_{i}_{query}",
                "product_name": title,
                "supply_price_krw": price,
                "image_url": "",
                "link": "",
                "price_1p_sgd": None,
                "price_1p_krw": None,
                "price_2p_sgd": None,
                "price_2p_krw": None,
                "price_3p_sgd": None,
                "price_3p_krw": None,
            })
    return items


def run():
    cfg = load_config()
    queries = cfg.get("sourcing_keywords", ["생수", "음료", "과자"])
    all_rows = []
    with sync_playwright() as pw:
        ctx = get_chrome_context(pw)
        page = ctx.new_page()
        for q in queries:
            if len(all_rows) >= 200:
                break
            try:
                items = try_coupang(page, q)
                all_rows.extend(items)
                print(f"[+] Coupang sourced: {len(items)}")
            except Exception as e:
                print(f"[!] Coupang error: {e}")
            if len(all_rows) < 100:
                try:
                    items = try_kurly(page, q)
                    all_rows.extend(items)
                    print(f"[+] Kurly sourced: {len(items)}")
                except Exception as e:
                    print(f"[!] Kurly error: {e}")
        ctx.close()

    if not all_rows:
        print("[!] No products from any source")
        return None
    return save_sourcing(all_rows, "multi")
