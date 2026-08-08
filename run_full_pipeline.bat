@echo off
title Shopee Full Pipeline
cd /d "%~dp0"
python sg_naver_sourcing.py
python full_pipeline.py %*
