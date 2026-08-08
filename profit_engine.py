"""
profit_engine.py: 1P/2P/3P 세트 가격 계산 + 공급사 합배송 추천 + 마진 30% 확보
"""
import os
import pandas as pd


class ProfitEngine:
    def __init__(self, country_rules, col_map):
        self.country_rules = country_rules
        self.col_map = col_map

    def calculate_qty_prices(self, row, country_code):
        rules = self.country_rules.get(country_code)
        if not rules:
            return None, "Country rules not found"
        try:
            supply_price_val = row.get(self.col_map.get("supply_price"), 0)
            supply_price = float(supply_price_val) if not pd.isna(supply_price_val) else 0.0
        except ValueError:
            return None, "Invalid supply price"
        try:
            weight_val = row.get(self.col_map.get("weight_g"), 0)
            weight_g = float(weight_val) if not pd.isna(weight_val) else 0.0
        except ValueError:
            weight_g = 0.0
        max_weight = rules.get("max_weight_g", 300)
        if weight_g > max_weight:
            return None, f"Exceeded max weight ({weight_g}g > {max_weight}g)"
        exchange_rate = rules.get("exchange_rate_krw", 1000.0)

        # 도매매 원장의 실제 국내 배송비를 동적으로 추출 (없을 시 기본 3,000원 적용)
        try:
            dome_ship_val = row.get(self.col_map.get("shipping_fee"), 3000)
            domeggeme_shipping = float(dome_ship_val) if not pd.isna(dome_ship_val) else 3000.0
        except ValueError:
            domeggeme_shipping = 3000.0
        fixed_forwarding_fee = 2000  # 배대지 고정비 무조건 가산
        handling = 1200              # 3PL 준비 수수료
        shopee_fee_ratio = 0.13      # 수수료율
        margin_ratio = 0.30          # 순수 마진율 30% 확보
        vat_ratio = rules.get("vat_ratio", 0.09)
        sls_base = 0.0
        sls_per_g = 0.0
        if country_code == "SG":
            sls_base = rules.get("sls_shipping_base_sgd", 1.99)
            sls_per_g = rules.get("sls_shipping_per_g_sgd", 0.015)
        elif country_code == "MY":
            sls_base = rules.get("sls_shipping_base_myr", 4.50)
            sls_per_g = rules.get("sls_shipping_per_g_myr", 0.03)
        denominator = 1.0 - shopee_fee_ratio - margin_ratio
        if denominator <= 0:
            return None, "Invalid margin/fee denominator"
        results = {}
        # 1P, 2P, 3P 가격 생성 루프
        for qty in [1, 2, 3]:
            qty_weight = weight_g * qty
            sls_shipping_foreign = sls_base + (qty_weight * sls_per_g)
            sls_shipping_krw = sls_shipping_foreign * exchange_rate
            # [수정] 물류 고정비(도매매 배송비 + 배대지비 2000 + 핸들링 1200) 반영 총 원가 공식
            total_cost_krw = (supply_price * qty) + domeggeme_shipping + fixed_forwarding_fee + handling + sls_shipping_krw

            target_price_krw = total_cost_krw / denominator
            target_price_krw_taxed = target_price_krw * (1.0 + vat_ratio)
            target_price_foreign = target_price_krw_taxed / exchange_rate
            results[f"price_{qty}p_foreign"] = round(target_price_foreign, 2)
            results[f"price_{qty}p_krw"] = round(target_price_krw_taxed, 0)
        return results, None

    def optimize_products(self, df, country_code, factory_dir):
        if df.empty:
            return pd.DataFrame(), []
        supplier_col = self.col_map.get("supplier_id", "공급사코드")
        product_col = self.col_map.get("product_id")

        # 합배송 가능한 동일 공급사의 우량 공급처 추천 로직 자동 가동
        recommendations = []
        if supplier_col in df.columns:
            supplier_counts = df[supplier_col].value_counts()
            rec_suppliers = supplier_counts[supplier_counts >= 3]

            if not rec_suppliers.empty:
                recommendations.append("=== [공급사 합배송 추천 리스트 (3개 이상 소싱 가능)] ===")
                for s_id, count in rec_suppliers.items():
                    recommendations.append(f"공급사 ID: {s_id} (등록 가능 상품수: {count}개)")

                rec_path = os.path.join(factory_dir, "02_Output", "공급사_합배송_추천리스트.txt")
                with open(rec_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(recommendations))
                print(f"[+] Written supplier recommendations to: {rec_path}")
        survived = []
        rejected = []
        for idx, row in df.iterrows():
            p_id = str(row.get(product_col, ""))
            p_name = str(row.get(self.col_map.get("product_name"), ""))

            calc, err = self.calculate_qty_prices(row, country_code)
            if err:
                rejected.append({"product_id": p_id, "product_name": p_name, "reason": err})
                continue

            row_copy = row.copy()
            for key, val in calc.items():
                row_copy[key] = val

            survived.append(row_copy)
        return pd.DataFrame(survived) if survived else pd.DataFrame(), rejected
