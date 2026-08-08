"""
sg_naver_sourcing.py
- Naver Shopping API 검색
- mallName == 쿠팡 / 마켓컬리 필터
- SG 가격 계산 후 엑셀 출력
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "00_System_Rules", "shopee_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def search_naver(config):
    naver = config["naver"]
    client_id = naver["client_id"]
    client_secret = naver["client_secret"]

    if not client_id or not client_secret:
        raise RuntimeError("naver client_id / client_secret 필요")

    query = naver.get("query", "쿠팡")
    display = naver.get("display", 100)
    endpoint = naver.get("search_endpoint", "https://openapi.naver.com/v1/search/shop.json")
    params = urllib.parse.urlencode({"query": query, "display": display})
    req = urllib.request.Request(f"{endpoint}?{params}", headers={
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "User-Agent": "Mozilla/5.0",
    })

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    items = data.get("items", [])
    mall_filter = [m.strip() for m in naver.get("mall_name_filter", ["쿠팡", "마켓컬리"]) if m.strip()]
    filtered = []
    for it in items:
        mall = str(it.get("mallName", "")).strip()
        if mall in mall_filter:
            filtered.append({
                "product_id": str(it.get("productId", "")),
                "product_name": it.get("title", ""),
                "supply_price_krw": int(it.get("lprice", 0)),
                "mall_name": mall,
                "image_url": it.get("image", ""),
                "link": it.get("link", ""),
            })
    return filtered


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


def run():
    config = load_config()
    print("[*] Naver sourcing started")
    items = search_naver(config)
    print(f"[*] Raw items: loaded={len(items)}")

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
    print(f"[+] Sourcing done: {len(df)} items -> {path}")
    return path


if __name__ == "__main__":
    run()
