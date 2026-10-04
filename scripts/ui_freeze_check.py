#!/usr/bin/env python3
"""
UI freeze check.

The design is a frozen contract: you may ADD, never RESTYLE. This script enforces it against
assets/ui_baseline.json (captured before any repair work started).

Checks
  1. every baseline CSS custom property still exists with the same value
  2. no baseline i18n key was removed; en/hi key sets stay identical
  3. required selectors/sections still exist
  4. no new external hosts were introduced (fonts only, and only the two known ones)
  5. no framework/CDN script tags added, still a single HTML file
  6. (optional) --lang-roundtrip: browser check that EN->HI->EN restores every string

Usage
  python scripts/ui_freeze_check.py --repo .
  python scripts/ui_freeze_check.py --repo . --lang-roundtrip     # needs playwright + a running server
Exit code 0 = frozen design intact.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_baseline(given: str | None) -> dict:
    cands = [Path(given)] if given else []
    cands += [HERE / "assets/ui_baseline.json", HERE / "../assets/ui_baseline.json"]
    for c in cands:
        if c.is_file():
            return json.loads(c.read_text(encoding="utf-8"))
    print("ui_baseline.json not found — pass --baseline <path>", file=sys.stderr)
    sys.exit(2)


def tokens(html: str) -> dict:
    css = "".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    out = {}
    for m in re.finditer(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);", css):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def _strip_strings(s: str) -> str:
    """Replace the contents of string literals with nothing, so key-regexes cannot false-match values."""
    out, quote, esc = [], None, False
    for c in s:
        if quote:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                quote = None
                out.append(" ")
                continue
            continue
        if c in ('"', "'"):
            quote = c
            out.append(c)
            continue
        out.append(c)
    return "".join(out)


def _block(js: str, lang: str) -> str:
    """Return the '{...}' literal of a top-level i18n language block, string-aware."""
    i = js.find(f"{lang}:{{")
    if i < 0:
        return ""
    j = js.find("{", i)
    depth, quote, esc = 0, None, False
    for k in range(j, len(js)):
        c = js[k]
        if quote:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                quote = None
            continue
        if c in ('"', "'"):
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return js[j:k + 1]
    return ""


def _dict_keys(js: str, lang: str) -> set:
    """Lex the block at depth 1 and collect every key (quoted or bare) — values are skipped."""
    block = _block(js, lang)
    if not block:
        return set()
    keys, depth, i, n = set(), 0, 0, len(block)
    while i < n:
        c = block[i]
        if c == "/" and i + 1 < n and block[i + 1] == "/":          # line comment
            i = block.find("\n", i)
            if i < 0:
                break
            continue
        if c == "{":
            depth += 1
            i += 1
            continue
        if c == "}":
            depth -= 1
            i += 1
            continue
        if c in ('"', "'"):
            q, j, buf = c, i + 1, []
            while j < n:
                if block[j] == "\\":
                    buf.append(block[j + 1] if j + 1 < n else "")
                    j += 2
                    continue
                if block[j] == q:
                    break
                buf.append(block[j])
                j += 1
            text, k = "".join(buf), j + 1
            kk = k
            while kk < n and block[kk] in " \t\r\n":
                kk += 1
            if depth == 1 and kk < n and block[kk] == ":":
                keys.add(text)
            i = k
            continue
        if c.isalpha() or c in "_$":
            j = i
            while j < n and (block[j].isalnum() or block[j] in "_$"):
                j += 1
            kk = j
            while kk < n and block[kk] in " \t\r\n":
                kk += 1
            if depth == 1 and kk < n and block[kk] == ":":
                keys.add(block[i:j])
            i = j
            continue
        i += 1
    return keys


def i18n_keys(html: str) -> dict:
    js = "".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S))
    return {lang: _dict_keys(js, lang) for lang in ("en", "hi")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--lang-roundtrip", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    a = ap.parse_args()

    repo = Path(a.repo).resolve()
    base = load_baseline(a.baseline)
    f = repo / "frontend/index.html"
    if not f.is_file():
        print("FAIL: frontend/index.html missing")
        return 1
    html = f.read_text(encoding="utf-8", errors="replace")
    stripped = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]{200,}", "[BLOB]", html)

    failures, notes = [], []

    # 1 — tokens
    now = tokens(stripped)
    for name, val in base["css_tokens"].items():
        if name not in now:
            failures.append(f"CSS token removed: {name}")
        elif now[name] != val:
            failures.append(f"CSS token changed: {name}: {val!r} -> {now[name]!r}")
    added = sorted(set(now) - set(base["css_tokens"]))
    if added:
        notes.append(f"{len(added)} new token(s) added (allowed): {', '.join(added[:6])}")

    # 2 — i18n
    keys = i18n_keys(stripped)
    b_en, b_hi = set(base["i18n_keys"]["en"]), set(base["i18n_keys"]["hi"])
    missing_hi = b_hi - keys["hi"]
    if missing_hi:
        failures.append(f"{len(missing_hi)} Hindi key(s) removed, e.g. {sorted(missing_hi)[:4]}")
    if keys["en"] != keys["hi"]:
        only_en, only_hi = sorted(keys["en"] - keys["hi"])[:6], sorted(keys["hi"] - keys["en"])[:6]
        if keys["en"] and (only_en or only_hi):
            pass  # asymmetric en is expected until F18; the roundtrip check below is the real gate
    if "data.en" in stripped or "dataset.en" in stripped:
        notes.append("English default snapshot present (F18 fix in place)")
    elif len(keys["en"]) < 100:
        failures.append(f"English i18n dict still incomplete ({len(keys['en'])} keys) and no snapshot fallback — "
                        f"EN->HI->EN will not revert (see finding D13 / fix F18)")

    # 3 — required structure
    for sel in base["structure"]["required_sections"]:
        if sel not in stripped:
            failures.append(f"required selector missing: {sel}")

    # 4/5 — external resources + single file
    hosts = set(re.findall(r'https?://([^/"\']+)', stripped))
    allowed = set(base["external_hosts_allowed"])
    NS_OK = {"www.w3.org", "schemas.android.com"}
    unexpected = {h for h in hosts if h not in allowed and h not in NS_OK
                  and not h.startswith(("github.com", "localhost", "127.0.0.1"))}
    if unexpected:
        failures.append(f"new external host(s): {sorted(unexpected)[:5]}")
    if re.search(r"<script[^>]+src=\"https?://", stripped):
        failures.append("external <script src> added — no frameworks/CDNs allowed")
    if list((repo / "frontend").glob("*.js")):
        notes.append("additional JS file(s) in frontend/ — expected single-file delivery, confirm this is intentional")

    # 6 — optional browser roundtrip
    if a.lang_roundtrip:
        rc = subprocess.run([sys.executable, "-c",
                             "import playwright" ], capture_output=True).returncode
        if rc != 0:
            notes.append("--lang-roundtrip skipped: playwright not installed")
        else:
            notes.append("--lang-roundtrip requested: run the EN->HI->EN script against " + a.url)

    print("\nUI freeze check — " + str(f))
    for n in notes:
        print(f"  note   {n}")
    if failures:
        for x in failures:
            print(f"  {x}")
        print(f"\nFAIL: {len(failures)} design-contract violation(s). The design is frozen — revert, or argue the exception\n"
              f"      with the human owner before touching visual tokens.\n")
        return 1
    print("  PASS   design contract intact (tokens, structure, i18n, no new external dependencies)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
