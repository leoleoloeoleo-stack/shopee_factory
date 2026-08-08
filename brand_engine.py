"""
brand_engine.py: 상품명에 [K-Design] / - Premium Korea Direct 브랜딩 샌드위치 적용
"""


class BrandEngine:
    def __init__(self, prefix="[K-Design] ", suffix=" - Premium Korea Direct", max_len=255):
        self.prefix = prefix
        self.suffix = suffix
        self.max_len = max_len

    def apply_branding(self, title):
        title = title.strip()
        branded_title = f"{self.prefix}{title}{self.suffix}"

        if len(branded_title) > self.max_len:
            allowed_title_len = self.max_len - len(self.prefix) - len(self.suffix)
            truncated_title = title[:allowed_title_len].strip()
            branded_title = f"{self.prefix}{truncated_title}{self.suffix}"

        return branded_title
