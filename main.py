#!/usr/bin/env python3
"""
OHPR Media Monitor — CLI entry point.

Usage:
    python main.py <url>
    python main.py <url> --pretty
    python main.py <url> --output result.json
    python main.py <url> --pretty --output result.json

Output is strict JSON written to stdout (or --output file).
Diagnostic messages go to stderr so stdout remains machine-parseable.
"""
from __future__ import annotations

import argparse
import json
import sys

from ohpr.pipeline import process_url


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ohpr",
        description="Extract and classify a news/article URL for media monitoring.",
    )
    parser.add_argument("url", help="Article URL to process")
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Pretty-print JSON output (indent=2)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Write JSON output to FILE instead of stdout",
    )
    args = parser.parse_args()

    result = process_url(args.url)

    indent = 2 if args.pretty else None
    output = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output)
                fh.write("\n")
            print(f"[ohpr] result written to {args.output}", file=sys.stderr)
        except OSError as exc:
            print(f"[ohpr] could not write to {args.output}: {exc}", file=sys.stderr)
            return 1
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
