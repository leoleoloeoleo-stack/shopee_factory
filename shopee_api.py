"""
shopee_api.py
- Shopee Open Platform API v2 HMAC signing + image upload + product add
"""
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urljoin

import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "00_System_Rules", "shopee_config.json")


class ShopeeClient:
    def __init__(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        s = cfg["shopee"]
        self.partner_id = s["partner_id"]
        self.partner_key = s["partner_key"]
        self.shop_id = int(s["shop_id"])
        self.access_token = s["access_token"]
        self.base = s.get("api_base", "https://partner.shopeemobile.com/api/v2")
        self.country = s.get("country", "SG")
        self._session = requests.Session()

    def _sign(self, path, ts):
        base_str = f"{self.partner_id}{path}{ts}{self.shop_id}{self.access_token}"
        return hmac.new(
            self.partner_key.encode("utf-8"),
            base_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(self, endpoint, payload=None):
        ts = int(time.time())
        path = f"/api/v2/{endpoint}"
        sign = self._sign(path, ts)
        url = urljoin(self.base, path)
        params = {
            "partner_id": self.partner_id,
            "timestamp": ts,
            "shop_id": self.shop_id,
            "access_token": self.access_token,
            "sign": sign,
            "sign_by": "partner",
        }
        resp = self._session.post(url, params=params, json=payload or {}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error") or data.get("error_open") or data.get("msg") == "error":
            raise RuntimeError(f"Shopee API error: {data}")
        return data

    def upload_image(self, image_url):
        if not image_url:
            return ""
        try:
            img = requests.get(image_url, timeout=20)
            img.raise_for_status()
        except Exception:
            return ""
        payload = {
            "image": f"data:image/jpeg;base64,{__import__('base64').b64encode(img.content).decode('utf-8')}"
        }
        data = self._request("media_space/upload_image", payload=payload)
        return data.get("response", {}).get("image_info", {}).get("image_url", "")

    def add_product(self, product):
        return self._request("product/add_product", payload=product)
