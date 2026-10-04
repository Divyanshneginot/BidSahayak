#!/usr/bin/env python3
"""
UI Freeze Checker for BidSahayak (Design Freeze Guardian).
Ensures frontend/index.html preserves core styling, tokens, section order,
and design system constraints without unauthorized regressions.
"""
import os
import sys
import re

REQUIRED_TOKENS = [
    "--ink", "--paper", "--hl", "--status-met", "--status-gap",
    "--status-exempt", "--status-review", "--mono", "--sans"
]

REQUIRED_SECTION_ORDER = [
    "top", "evidence", "demo", "result", "source", "trace"
]

def check_ui_freeze(repo_root: str = ".") -> bool:
    index_path = os.path.join(repo_root, "frontend", "index.html")
    if not os.path.exists(index_path):
        print(f"[FAIL] frontend/index.html not found at {index_path}")
        return False

    with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    # 1. Check Tokens
    missing_tokens = [t for t in REQUIRED_TOKENS if t not in html]
    if missing_tokens:
        print(f"[FAIL] Missing design tokens: {missing_tokens}")
        return False

    # 2. Check Section Order
    positions = []
    for s in REQUIRED_SECTION_ORDER:
        pos = html.find(f'id="{s}"')
        if pos == -1:
            pos = html.find(f"id='{s}'")
        if pos == -1:
            print(f"[FAIL] Missing required section #{s}")
            return False
        positions.append((s, pos))

    ordered = [s for s, _ in sorted(positions, key=lambda x: x[1])]
    if ordered != REQUIRED_SECTION_ORDER:
        print(f"[FAIL] Section order altered: expected {REQUIRED_SECTION_ORDER}, got {ordered}")
        return False

    # 3. Check Core Components
    required_ids = ["themeTgl", "langTgl", "menuTgl", "dropzone", "fileInput", "result"]
    missing_ids = [i for i in required_ids if f'id="{i}"' not in html and f"id='{i}'" not in html]
    if missing_ids:
        print(f"[FAIL] Missing core element IDs: {missing_ids}")
        return False

    print("[PASS] UI Freeze Check: Design tokens, layout structure, and section order intact.")
    return True

if __name__ == "__main__":
    repo = "."
    if len(sys.argv) > 2 and sys.argv[1] == "--repo":
        repo = sys.argv[2]
    ok = check_ui_freeze(repo)
    sys.exit(0 if ok else 1)
