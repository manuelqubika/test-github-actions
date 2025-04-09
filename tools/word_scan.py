#!/usr/bin/python
# Copyright(C) 2025 Advanced Micro Devices, Inc. All rights reserved.

import os
import sys
import argparse

def get_words_from_env_or_args():
    parser = argparse.ArgumentParser(description='Scan file(s) for a list of words.')
    parser.add_argument('path', help='File or directory to scan')
    parser.add_argument('--words', help='Comma-separated list of words to search for')
    args = parser.parse_args()

    word_list_str = args.words or os.getenv("WORDS")
    if not word_list_str:
        print("❌ Error: No word list provided via --words or WORDS environment variable.")
        sys.exit(2)

    words = [w.strip().lower() for w in word_list_str.split(',') if w.strip()]
    return args.path, words

def scan_file(filepath, words):
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line_lower = line.lower()
                if any(word in line_lower for word in words):
                    results.append((filepath, line_num, line.strip()))
    except (UnicodeDecodeError, FileNotFoundError, PermissionError):
        pass
    return results

def print_github_summary(results):
    for filepath, line_num, line in results:
        print(f"{filepath}:{line_num}: {line}")

def is_dry_run():
    return os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")

def append_to_github_summary(results):
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return

    with open(summary_file, 'a', encoding='utf-8') as f:
        if results:
            f.write("## 🚨 Forbidden Words Found\n\n")
            for filepath, line_num, line in results:
                f.write(f"- `{filepath}:{line_num}` → `{line}`\n")
            f.write("\n")


if __name__ == "__main__":
    path, words = get_words_from_env_or_args()
    matches = scan_file(path, words) if os.path.isfile(path) else []

    print_github_summary(matches)
    append_to_github_summary(matches)

    if matches:
        print("❌ Forbidden words found.")
        if is_dry_run():
            print("ℹ️ DRY_RUN is enabled. Not exiting with error.")
            sys.exit(0)
        else:
            sys.exit(1)
