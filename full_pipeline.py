"""
full_pipeline.py
- sourcing + upload 통합 실행
"""
import sys
from sg_naver_sourcing import run as sourcing_run
from shopee_uploader import run as upload_run


def main():
    dryrun = "--dryrun" in sys.argv
    print("[*] Full pipeline started")
    sourcing_run()
    print("[*] Upload phase started")
    results = upload_run(dryrun=dryrun)
    print(f"[+] Pipeline done: {len(results)} items processed")


if __name__ == "__main__":
    main()
