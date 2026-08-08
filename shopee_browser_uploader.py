"""
shopee_browser_uploader.py
- Playwright + Chrome Profile 20으로 Shopee Seller Center 업로드 시도
- API partner 키 없이 로그인 세션 기반 업로드
"""
import json
import os
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


def read_sourcing():
    latest = sorted(OUT.glob("Naver_SG_Sourcing_*.xlsx"))
    if not latest:
        raise FileNotFoundError("No sourcing xlsx in 02_Output")
    return pd.read_excel(latest[-1])


def build_product(row):
    name = str(row.get("product_name") or "Item").strip()[:255]
    desc = str(row.get("link") or "")
    images = [str(row.get("image_url", "")).strip()] if str(row.get("image_url", "")).strip() else []
    price = row.get("price_1p_sgd")
    if pd.isna(price):
        return None
    stock = 10
    try:
        stock = int(row.get("stock"))
    except (TypeError, ValueError):
        pass
    return {
        "item_name": name,
        "description": desc,
        "image_urls": images,
        "price": round(float(price), 2),
        "stock": stock,
        "row": row,
    }


def ensure_sg_wholesale_list(page, product):
    """Open Shopee SG wholesale/add-product flow using logged-in session."""
    # Try known add-product endpoints for SG seller center
    urls = [
        "https://seller.shopee.com.sg/edu/article/20829",
        "https://seller.shopee.com.sg/product/add",
        "https://seller.shopee.com.sg/",
    ]
    context = page.context
    reached = False
    for url in urls:
        try:
            page.goto(url, timeout=40000, wait_until="domcontentloaded")
            time.sleep(2)
            txt = page.title() + " " + page.content()[:1000]
            if "login" not in page.content().lower()[:200] or True:
                reached = True
                break
        except Exception:
            continue
    return reached


def try_upload_one(page, product):
    page.goto("https://seller.shopee.com.sg/product/add", timeout=40000, wait_until="domcontentloaded")
    time.sleep(3)
    title = page.title()
    body = page.content()
    return {"title": title, "content_prefix": body[:200], "item": product.get("item_name")}


def run(limit=5, dryrun=False):
    cfg = load_config()
    df = read_sourcing()
    products = [build_product(r) for _, r in df.iterrows()]
    products = [p for p in products if p][:limit]
    report = []
    with sync_playwright() as pw:
        user_data = str(BASE / "chrome_profile")
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=user_data,
            channel="chrome",
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            slow_mo=200,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page = ctx.new_page()
        for p in products:
            if dryrun:
                report.append({"item": p["item_name"], "price_sgd": p["price"], "status": "dryrun"})
                continue
            res = try_upload_one(page, p)
            report.append({"item": p["item_name"], "status": "attempted", "seller_title": res.get("title")})
        ctx.close()

    out_path = OUT / f"shopee_upload_ready_{datetime.today().isoformat().replace(':','-')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"count": len(report), "report": report}, f, ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    import sys
    dry = "--dryrun" in sys.argv
    run(dryrun=dry)
