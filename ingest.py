"""
ingest.py: 도매매 CSV 파싱 + 공급사 스크래퍼 + 블랙리스트/재고/당일발송 필터링
"""
import os
import glob
import json
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_markdown_list(filepath):
    if not os.path.exists(filepath):
        return []
    items = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            match = re.match(r'^[-*]\s+(.+)$', line)
            if match:
                items.append(match.group(1).strip().lower())
    return items


def load_json_rule(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


class IngestParser:
    def __init__(self, factory_dir):
        self.factory_dir = factory_dir
        self.rules_dir = os.path.join(factory_dir, "00_System_Rules")

        config_path = os.path.join(factory_dir, "config.json")
        self.config = load_config(config_path)
        self.col_map = self.config.get("column_mapping", {})

        self.blacklist_brands = load_markdown_list(os.path.join(self.rules_dir, "blacklist_brands.md"))
        self.blacklist_keywords = load_markdown_list(os.path.join(self.rules_dir, "blacklist_keywords.md"))
        self.forbidden_categories = load_json_rule(os.path.join(self.rules_dir, "forbidden_categories.json"))
        self.country_rules = load_json_rule(os.path.join(self.rules_dir, "country_rules.json"))

        # 공급사 ID 캐시 파일 연동 (속도 향상 및 중복 요청 방지)
        self.cache_path = os.path.join(self.rules_dir, "supplier_cache.json")
        self.supplier_cache = load_json_rule(self.cache_path)

    def save_supplier_cache(self):
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.supplier_cache, f, ensure_ascii=False, indent=2)

    def scrape_supplier_id(self, product_id):
        product_id = str(product_id).strip()
        if product_id in self.supplier_cache:
            return product_id, self.supplier_cache[product_id]

        url = f"https://domeggook.com/{product_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8', errors='ignore')

                # 다양한 HTML 구조 대응을 위한 정규표현식 매칭 리스트
                seller_patterns = [
                    r'sellerHome\.php\?sellerID=([a-zA-Z0-9_\-]+)',
                    r'seller_id\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']',
                    r'class=["\']seller_id["\'][^>]*>([^<]+)</a>',
                    r'/seller/\?id=([a-zA-Z0-9_\-]+)'
                ]

                for pat in seller_patterns:
                    match = re.search(pat, html, re.IGNORECASE)
                    if match:
                        seller_id = match.group(1).strip()
                        return product_id, seller_id

                return product_id, "UNKNOWN_SELLER"
        except Exception:
            return product_id, "UNKNOWN_SELLER"

    def fetch_suppliers_for_df(self, df):
        product_col = self.col_map.get("product_id")
        if product_col not in df.columns:
            return df

        product_ids = df[product_col].dropna().unique()
        to_scrape = [pid for pid in product_ids if str(pid) not in self.supplier_cache]

        if to_scrape:
            print(f"[*] {len(to_scrape)}개의 새로운 상품 공급사 정보를 스크래핑합니다...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(self.scrape_supplier_id, pid): pid for pid in to_scrape}
                for fut in as_completed(futures):
                    pid, seller_id = fut.result()
                    self.supplier_cache[str(pid)] = seller_id
            self.save_supplier_cache()

        supplier_col = self.col_map.get("supplier_id", "공급사코드")
        df[supplier_col] = df[product_col].astype(str).map(self.supplier_cache)
        return df

    def parse_csv_files(self):
        input_dir = os.path.join(self.factory_dir, "01_Input")
        csv_files = glob.glob(os.path.join(input_dir, "마이박스_*.csv"))

        all_dfs = []
        for file in csv_files:
            for encoding in ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']:
                try:
                    df = pd.read_csv(file, encoding=encoding)
                    sample_col = self.col_map.get("product_name")
                    if sample_col in df.columns:
                        all_dfs.append(df)
                        break
                except Exception:
                    continue

        if not all_dfs:
            return pd.DataFrame()

        merged_df = pd.concat(all_dfs, ignore_index=True)
        return self.fetch_suppliers_for_df(merged_df)

    def filter_products(self, df, country_code):
        rules = self.country_rules.get(country_code, {})
        min_stock = rules.get("min_stock", 50)
        forbidden_cats = self.forbidden_categories.get(country_code, [])

        survived = []
        rejected = []

        for idx, row in df.iterrows():
            p_id = str(row.get(self.col_map.get("product_id"), ""))
            p_name = str(row.get(self.col_map.get("product_name"), ""))
            brand = str(row.get(self.col_map.get("brand_name"), "")).strip().lower()
            category = str(row.get(self.col_map.get("category_id"), ""))

            stock_val = row.get(self.col_map.get("stock"), 0)
            try:
                stock = int(float(stock_val)) if not pd.isna(stock_val) else 0
            except ValueError:
                stock = 0

            delivery_type = str(row.get(self.col_map.get("delivery_type"), ""))

            if any(b in brand for b in self.blacklist_brands if b):
                rejected.append({"product_id": p_id, "product_name": p_name, "reason": f"Blacklisted Brand ({brand})"})
                continue

            p_name_lower = p_name.lower()
            found_keyword = [k for k in self.blacklist_keywords if k and k in p_name_lower]
            if found_keyword:
                rejected.append({"product_id": p_id, "product_name": p_name, "reason": f"Blacklisted Keyword ({found_keyword[0]})"})
                continue

            if category in forbidden_cats:
                rejected.append({"product_id": p_id, "product_name": p_name, "reason": f"Forbidden Category ({category})"})
                continue

            if stock < min_stock:
                rejected.append({"product_id": p_id, "product_name": p_name, "reason": f"Insufficient Stock ({stock} < {min_stock})"})
                continue

            if "당일" not in delivery_type:
                rejected.append({"product_id": p_id, "product_name": p_name, "reason": f"Not same-day shipping ({delivery_type})"})
                continue

            survived.append(row)

        return pd.DataFrame(survived) if survived else pd.DataFrame(), rejected
