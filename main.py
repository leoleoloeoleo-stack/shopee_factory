"""
main.py: Shopee 자동화 파이프라인 오케스트레이터
- 도매매 CSV → 필터 → 마진계산 → 브랜딩 → 엑셀/텍스트 출력 → 로그 기록 → 옵시디언 반영
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from ingest import IngestParser
from profit_engine import ProfitEngine
from brand_engine import BrandEngine
from exporter import Exporter


def setup_directories(base_dir):
    dirs = [
        os.path.join(base_dir, "00_System_Rules"),
        os.path.join(base_dir, "01_Input"),
        os.path.join(base_dir, "02_Output"),
        os.path.join(base_dir, "logs")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def write_log(base_dir, country_code, total_parsed, survived_count, rejected_list):
    log_dir = os.path.join(base_dir, "logs")
    today_str = datetime.today().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f"log_{today_str}.md")

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n# Execution Run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Target: {country_code}\n\n")
        f.write(f"- **Total Products Parsed**: {total_parsed}\n")
        f.write(f"- **Survived / Upload Ready**: {survived_count}\n")
        f.write(f"- **Rejected Count**: {len(rejected_list)}\n\n")

        f.write("## Rejected Products List\n\n")
        if not rejected_list:
            f.write("No products were filtered out.\n")
        else:
            f.write("| Product ID | Product Name | Exclusion Reason |\n")
            f.write("| --- | --- | --- |\n")
            for item in rejected_list:
                f.write(f"| {item['product_id']} | {item['product_name']} | {item['reason']} |\n")
        f.write("\n---\n")


def run_pipeline(country_code="SG"):
    factory_dir = os.path.dirname(os.path.abspath(__file__))
    setup_directories(factory_dir)

    print(f"[*] Starting Shopee Sourcing & Uploading Automation for {country_code}...")

    parser = IngestParser(factory_dir)
    df_raw = parser.parse_csv_files()

    if df_raw.empty:
        print("[!] No Domeggeme CSV files matching '마이박스_*.csv' found in 01_Input/.")
        return

    total_parsed = len(df_raw)
    print(f"[*] Successfully loaded {total_parsed} raw products.")

    df_ingested, rejected_ingest = parser.filter_products(df_raw, country_code)
    print(f"[*] Surviving ingest phase: {len(df_ingested)} products.")

    # 3. 마진 계산 및 필터링 (1P/2P/3P 가격 생성 + 공급사 합배송 분석)
    profit_engine = ProfitEngine(parser.country_rules, parser.col_map)
    df_optimized, rejected_profit = profit_engine.optimize_products(df_ingested, country_code, factory_dir)

    survived_count = len(df_optimized)
    print(f"[*] Surviving margin calculations: {survived_count} products.")

    all_rejected = rejected_ingest + rejected_profit

    # 4. 브랜딩 및 엑셀/텍스트 출력
    if not df_optimized.empty:
        brand_engine = BrandEngine()
        exporter = Exporter(os.path.join(factory_dir, "02_Output"), parser.col_map)
        name_col = parser.col_map.get("product_name")

        df_optimized["branded_name"] = df_optimized[name_col].apply(brand_engine.apply_branding)

        excel_path = exporter.export_excel(df_optimized, f"Shopee_Upload_Ready_{country_code}.xlsx")
        chunk_files = exporter.export_comma_chunks(df_optimized)

        print(f"[+] Excel generated at: {excel_path}")
        print(f"[+] Generated {len(chunk_files)} comma-separated batch text files.")
    else:
        print("[!] No products survived filters. Nothing exported.")

    write_log(factory_dir, country_code, total_parsed, survived_count, all_rejected)
    print("[*] Pipeline complete. Logs written to logs/ directory.")

    # 옵시디언 연동: 산출물을 obsidian_kb/02_쇼핑몰_리셀/Shopee_Factory/<date>/ 아래로 복사
    try:
        from datetime import date as _date
        today = _date.today().isoformat()
        obs_target = Path(r"C:\돈벌자\obsidian_kb\02_쇼핑몰_리셀\Shopee_Factory") / today
        obs_target.mkdir(parents=True, exist_ok=True)
        # 규칙 파일 복사 (최신 상태 유지)
        rules_src = Path(factory_dir) / "00_System_Rules"
        rules_dst = obs_target / "00_System_Rules"
        if rules_src.exists():
            if rules_dst.exists():
                shutil.rmtree(rules_dst)
            shutil.copytree(rules_src, rules_dst)
        # 산출물 복사
        out_src = Path(factory_dir) / "02_Output"
        out_dst = obs_target / "02_Output"
        if out_src.exists():
            if out_dst.exists():
                shutil.rmtree(out_dst)
            shutil.copytree(out_src, out_dst)
        # 로그 복사
        logs_src = Path(factory_dir) / "logs"
        logs_dst = obs_target / "logs"
        if logs_src.exists():
            if logs_dst.exists():
                shutil.rmtree(logs_dst)
            shutil.copytree(logs_src, logs_dst)
        print(f"[+] Obsidian mirror updated at: {obs_target}")
    except Exception as e:
        print(f"[!] Obsidian mirror update failed: {e}")


if __name__ == "__main__":
    target_country = "SG"
    if len(sys.argv) > 1:
        target_country = sys.argv[1].upper()
    run_pipeline(target_country)
