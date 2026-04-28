#!/usr/bin/env python3
"""
Quick test — run this file directly to process the sample URLs.
Click the Run button (or: python test_run.py)
"""
import json
import sys
from ohpr.pipeline import process_url

URLS = [
    "https://www.calcalistech.com/ctechnews/article/bjjnqzl2wg",
    "https://www.mako.co.il/news-business/hi_tech/Article-8b92b2d4bee3d91026.htm",
]


def main() -> None:
    results = []
    for i, url in enumerate(URLS, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(URLS)}] Processing: {url}")
        print("=" * 60)
        result = process_url(url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        results.append(result)

    print(f"\n{'='*60}")
    print(f"Done — processed {len(results)} article(s).")


if __name__ == "__main__":
    main()
