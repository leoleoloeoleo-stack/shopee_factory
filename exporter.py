"""
exporter.py: Shopee 업로드용 엑셀 및 100개 단위 콤마 텍스트 배치 생성
"""
import os
import pandas as pd


class Exporter:
    def __init__(self, output_dir, col_map):
        self.output_dir = output_dir
        self.col_map = col_map
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def export_excel(self, df, filename="Shopee_Upload_Ready.xlsx"):
        if df.empty:
            return None

        export_data = []
        for idx, row in df.iterrows():
            export_data.append({
                "Product ID (상품번호)": row.get(self.col_map.get("product_id")),
                "Branded Name (상품명)": row.get("branded_name"),
                "Shopee Price (현지판매가)": row.get("calculated_price_foreign"),
                "KRW Price (원화환산가)": row.get("calculated_price_krw"),
                "Stock (재고)": row.get(self.col_map.get("stock")),
                "Category ID (카테고리번호)": row.get(self.col_map.get("category_id")),
                "Weight (무게)": row.get(self.col_map.get("weight_g")),
                "Image URL (대표이미지)": row.get(self.col_map.get("image_url")),
                "Domeggeme Cost (원가)": row.get(self.col_map.get("supply_price")),
                "Estimated Profit KRW (예상수익)": row.get("estimated_profit_krw"),
                "SLS Shipping KRW (SLS배송비)": row.get("sls_shipping_krw")
            })
        export_df = pd.DataFrame(export_data)
        filepath = os.path.join(self.output_dir, filename)
        export_df.to_excel(filepath, index=False)
        return filepath

    def export_comma_chunks(self, df, chunk_size=100):
        if df.empty:
            return []
        product_ids = df[self.col_map.get("product_id")].astype(str).tolist()
        chunk_files = []

        for i in range(0, len(product_ids), chunk_size):
            chunk = product_ids[i:i + chunk_size]
            comma_string = ",".join(chunk)

            chunk_num = (i // chunk_size) + 1
            filename = f"batch_{chunk_num}.txt"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(comma_string)
            chunk_files.append(filepath)

        return chunk_files
