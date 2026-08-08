import pandas as pd, re
from pathlib import Path

base = Path(r'C:\돈벌자\Shopee_Factory\02_Output')
src = base / 'Naver_SG_Sourcing_2026-07-05.xlsx'
out = base / 'Shopee_Ready_Cosmetic_2026-07-05.xlsx'

df = pd.read_excel(src)

CATEGORY_RE = re.compile(r'화장품|스킨|로션|크림|클렌징|선크림|립스틱|마스크팩|에센스|세럼|기미|미백|주름|탄력|수분', re.I)

def parse_price(text):
    if pd.isna(text):
        return None
    text = re.sub(r'[^0-9]', '', str(text))
    if not text:
        return None
    try:
        return float(text)
    except:
        return None

def extract_weight_g(text):
    if pd.isna(text):
        return None
    text = str(text)
    m = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|L)', text, re.I)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit == 'kg':
        val *= 1000
    elif unit == 'l':
        val *= 1000
    return val

prices = df['supply_price_krw'].apply(parse_price)
weights = df['product_name'].apply(extract_weight_g)

m1 = df['product_name'].str.contains(CATEGORY_RE, na=False).astype(int)
m2 = prices.notna().astype(int)
m3 = ((prices >= 15000) & (prices <= 30000)).astype(int)
m4 = (weights.notna() & (weights <= 500)).astype(int)

mask = (m1 + m2 + m3 + m4) == 4
filtered = df[mask].copy()
print('raw', len(df))
print('filtered', len(filtered))
if len(filtered):
    print(filtered[['product_name','supply_price_krw']].head(10).to_string(index=False))
    shopee = pd.DataFrame()
    shopee['product_name'] = filtered['product_name'].values
    shopee['supply_price_krw'] = prices[mask].values
    shopee['price_1p_krw'] = prices[mask].values
    shopee['price_2p_krw'] = prices[mask].values * 2
    shopee['price_3p_krw'] = prices[mask].values * 3
    shopee['weight_g'] = weights[mask].values
    shopee['image_url'] = filtered['image_url'].values
    shopee['link'] = filtered['link'].values
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        shopee.to_excel(writer, index=False, sheet_name='Shopee_Ready')
        filtered.to_excel(writer, index=False, sheet_name='Raw_Sourced')
    print('saved:', out)
else:
    print('No matches')
    print('category matches:', int(m1.sum()))
    print('price parsed:', int(m2.sum()))
    print('price in range:', int(m3.sum()))
    print('weight valid <=500:', int(m4.sum()))
    px = prices.dropna()
    w = weights.dropna()
    print('price stats:', px.min(), '-', px.max(), 'mean', px.mean())
    print('weight stats:', w.min(), '-', w.max(), 'mean', w.mean())
