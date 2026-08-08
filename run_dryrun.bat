@echo off
title Shopee Dry Run
cd /d "%~dp0"
python shopee_uploader.py --dryrun
