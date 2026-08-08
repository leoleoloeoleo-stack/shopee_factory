# HERMES 인수인계서 — Shopee 자동화 파이프라인

> 작성일: 2026-07-04
> 대상: 헤르메스 (Hermes Agent)
> 작업 범위: C:\돈벌자\Shopee_Factory

---

## 1. 목표

네이버 쇼핑 API로 쿠팡/마켓컬리 상품을 소싱 → SG 가격 계산 → Shopee에 자동 등록하는 파이프라인 구축.

---

## 2. 디렉토리 구조

```
Shopee_Factory/
├── 00_System_Rules/
│   ├── blacklist_brands.md
│   ├── blacklist_keywords.md
│   ├── country_rules.json
│   ├── forbidden_categories.json
│   └── shopee_config.json          ← 신규 생성됨
├── 01_Input/                       ← 기존 유지
├── 02_Output/                      ← 엑셀/로그 출력
├── logs/                           ← 실행 로그
├── main.py                         ← 기존 도매매 파이프라인
├── brand_engine.py
├── exporter.py
├── ingest.py
├── profit_engine.py
├── config.json
├── sg_naver_sourcing.py            ← 신규 생성됨
├── shopee_api.py                   ← 신규 생성됨
├── shopee_uploader.py              ← 신규 생성됨
├── full_pipeline.py                ← 신규 생성됨
├── run_full_pipeline.bat           ← 신규 생성됨
├── run_sourcing_only.bat           ← 신규 생성됨
├── run_upload_only.bat             ← 신규 생성됨
└── run_dryrun.bat                  ← 신규 생성됨
```

---

## 3. 신규 파일 설명

### 3.1 `sg_naver_sourcing.py`
네이버 쇼핑 API 검색 → 쿠팡/마켓컬리만 필터 → SG 가격 계산 → `02_Output/Naver_SG_Sourcing_{date}.xlsx` 출력

### 3.2 `shopee_api.py`
Shopee Open Platform API v2 HMAC 서명 + 이미지 업로드 + 상품 등록

### 3.3 `shopee_uploader.py`
최신 소싱 엑셀 읽어서 Shopee SG에 자동 등록, 업로드 결과 JSON 저장

### 3.4 `full_pipeline.py`
소싱 + 업로드 통합 오케스트레이터

---

## 4. 실행 방법

### 4.1 전체 파이프라인
```bash
cd C:\돈벌자\Shopee_Factory
python sg_naver_sourcing.py
python full_pipeline.py
```
또는 배치:
```
run_full_pipeline.bat 더블클릭
```

### 4.2 소싱만
```
run_sourcing_only.bat
```

### 4.3 업로드만 (기존 엑셀)
```
run_upload_only.bat
```

### 4.4 시뮬레이션 (실제 등록 안 함)
```
run_dryrun.bat
```

---

## 5. 설정

### 5.1 Naver API 키
파일: `00_System_Rules/shopee_config.json` 의 `naver.client_id`, `client_secret` 채우기

### 5.2 Shopee API 키
```
https://open.shopee.com
```
파트너 계정 생성 → 앱 생성 → 발급된 `partner_id`, `partner_key`
OAuth 인증으로 `shop_id`, `access_token` 획득 → `shopee_config.json` 입력

---

## 6. 다음 작업

1. Naver API 키 설정
2. Shopee 파트너 계정 생성 및 OAuth 인증
3. `run_dryrun.bat` 으로 시뮬레이션 검증
4. `run_full_pipeline.bat` 전체 실행 테스트

---

## 7. 주의사항

- Naver API 무료 한도: 일 25,000회
- Shopee 이미지는 썸네일 URL 기반 업로드, 도메인 차단 시 업로드 실패할 수 있음
- `price_1p_sgd` 기준 상품만 업로드 시도
- 카테고리 `100636` 은 기본값, 실제 업로드 전 Shopee 카테고리 매핑 확인 필요

---

## 8. 기존 파이프라인과의 관계

기존 `main.py` + 도매매 CSV 파이프라인은 그대로 유지.
신규 Naver API 소싱 파이프라인은 별도로 운영 가능.
반드시 다른 URL에서 영상 공개하지 말 것.