@echo off
title Shopee Upload Only
cd /d "%~dp0"
python shopee_uploader.py %*
