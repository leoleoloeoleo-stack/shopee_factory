"""
shopee_uploader.py
- Read latest Naver SG sourcing excel and register to Shopee SG
"""
import json
import os
from datetime import datetime

import pandas as pd
from shopee_api import ShopeeClient


def read_latest_sourcing():
    base_dir = os.path.dirname(__file__)
    out_dir = os.path.join(base_dir, "02_Output")
    today = datetime.today().strftime("%Y-%m-%d")
    path = os.path.join(out_dir, f"Naver_SG_Sourcing_{today}.xlsx")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return pd.read_excel(path)


def build_product(row):
    name = str(row.get("product_name") or "Item").strip()
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

    product = {
        "item_name": name[:255],
        "description": desc[:5000],
        "image": {"image_id_list": images},
        "original_price": {"price_list": [{"unit": 1, "amount": round(float(price), 2)}]},
        "weight": 0.5,
        "normal_stock": stock,
        "category_id": 100636,
    }
    return product


def run(dryrun=False):
    if dryrun:
        df = read_latest_sourcing()
        results = []
        payload_out = []
        for _, row in df.iterrows():
            item = build_product(row)
            if not item:
                continue
            results.append({"product_id": row.get("product_id"), "status": "dryrun", "name": item.get("item_name")})
            payload_out.append({"product_id": row.get("product_id"), "payload": item, "status": "dryrun"})
        out_dir = os.path.join(os.path.dirname(__file__), "02_Output")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"upload_results_{datetime.today().isoformat().replace(':','-')}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[dryrun] Skipped real upload; simulated {len(results)} products")
        return results

    client = ShopeeClient()
    df = read_latest_sourcing()
    results = []
    out_dir = os.path.join(os.path.dirname(__file__), "02_Output")
    os.makedirs(out_dir, exist_ok=True)
    local_path = os.path.join(out_dir, f"shopee_upload_ready_{datetime.today().isoformat()}.json")
    payload_out = []
    for _, row in df.iterrows():
        item = build_product(row)
        if not item:
            continue
        if dryrun:
            results.append({"product_id": row.get("product_id"), "status": "dryrun", "name": item.get("item_name")})
            payload_out.append({"product_id": row.get("product_id"), "payload": item, "status": "dryrun"})
            continue
        data = client.add_product(item)
        item_id = (
            data.get("response", {}).get("item_info", {}).get("item_id")
            or data.get("item_id")
        )
        results.append({
            "product_id": row.get("product_id"),
            "item_id": item_id,
            "status": "uploaded",
            "name": item.get("item_name"),
        })
    out_path = os.path.join(os.path.dirname(__file__), "02_Output", f"upload_results_{datetime.today().isoformat().replace(':','-')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    import sys
    run(dryrun="--dryrun" in sys.argv)
