"""
Impeccable Headless Audit for BidSahayak.
Tests all viewport sizes, light/dark themes, English/Hindi languages,
checks contrast, overflow, touch targets, broken textures, and interactive gates.
"""
import os
import sys
import json
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.makedirs("shots/impeccable", exist_ok=True)

VIEWPORTS = [
    {"name": "mobile-xs", "width": 320, "height": 640, "device": "iPhone SE 1st gen"},
    {"name": "mobile-sm", "width": 375, "height": 667, "device": "iPhone SE 2nd gen"},
    {"name": "mobile-md", "width": 390, "height": 844, "device": "iPhone 14"},
    {"name": "mobile-lg", "width": 414, "height": 896, "device": "iPhone 11 / XR"},
    {"name": "tablet-sm", "width": 600, "height": 960, "device": "Small tablet / phablet"},
    {"name": "tablet-lg", "width": 768, "height": 1024, "device": "iPad portrait"},
    {"name": "laptop-sm", "width": 1024, "height": 768, "device": "iPad landscape / Laptop"},
    {"name": "laptop-md", "width": 1280, "height": 800, "device": "Standard laptop"},
    {"name": "desktop-lg", "width": 1440, "height": 900, "device": "MacBook Pro / Desktop"},
    {"name": "wide-fhd", "width": 1920, "height": 1080, "device": "1080p FHD Display"},
]

def check_page_integrity(page, vp_name, theme, lang):
    """Deep inspection of layout, overflow, textures, and typography."""
    findings = []
    
    # 1. Horizontal overflow check
    overflow_data = page.evaluate("""() => {
        const docElem = document.documentElement;
        const body = document.body;
        const scrollW = Math.max(docElem.scrollWidth, body.scrollWidth);
        const clientW = window.innerWidth;
        const hasOverflow = scrollW > clientW;
        
        // Find overflowing elements
        const overflowingElements = [];
        if (hasOverflow) {
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                if (rect.right > clientW + 1.5) {
                    overflowingElements.push({
                        tag: el.tagName,
                        id: el.id,
                        className: el.className,
                        right: Math.round(rect.right),
                        width: Math.round(rect.width),
                        viewportWidth: clientW
                    });
                    if (overflowingElements.length >= 5) break;
                }
            }
        }
        return { scrollW, clientW, diff: scrollW - clientW, hasOverflow, overflowingElements };
    }""")
    
    if overflow_data["hasOverflow"]:
        findings.append({
            "dimension": "Responsive",
            "severity": "P1",
            "desc": f"Horizontal overflow by {overflow_data['diff']}px (scrollW={overflow_data['scrollW']}, innerW={overflow_data['clientW']})",
            "details": overflow_data["overflowingElements"]
        })
        
    # 2. Broken image / textures check
    broken_assets = page.evaluate("""() => {
        const imgs = Array.from(document.querySelectorAll('img')).filter(img => !img.complete || img.naturalWidth === 0);
        return imgs.map(i => ({ src: i.src ? i.src.substring(0, 80) : '', id: i.id, alt: i.alt }));
    }""")
    if broken_assets:
        findings.append({
            "dimension": "Performance",
            "severity": "P0",
            "desc": f"Broken image textures found: {len(broken_assets)}",
            "details": broken_assets
        })

    # 3. Hidden or unrevealed .rv elements
    unrevealed = page.evaluate("""() => {
        const rv = Array.from(document.querySelectorAll('.rv:not(.in)'));
        return rv.length;
    }""")
    if unrevealed > 0:
        findings.append({
            "dimension": "Implementation Integrity",
            "severity": "P2",
            "desc": f"Unrevealed animation elements: {unrevealed} elements still have .rv without .in"
        })

    # 4. Touch target size check on mobile (<500px)
    if overflow_data["clientW"] <= 480:
        touch_targets = page.evaluate("""() => {
            const clickables = Array.from(document.querySelectorAll('button, a.btn, .tgl, .approve-mini'));
            const undersized = [];
            for (const el of clickables) {
                const rect = el.getBoundingClientRect();
                // Visible elements only
                if (rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32)) {
                    undersized.push({
                        text: el.innerText.trim().substring(0, 20),
                        tag: el.tagName,
                        id: el.id,
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    });
                }
            }
            return undersized;
        }""")
        if touch_targets:
            findings.append({
                "dimension": "Accessibility",
                "severity": "P2",
                "desc": f"Undersized touch targets on mobile: {len(touch_targets)} interactive elements < 32px height/width",
                "details": touch_targets
            })

    # 5. Contrast and color collision check
    contrast_check = page.evaluate("""() => {
        const bodyBg = getComputedStyle(document.body).backgroundColor;
        const bodyColor = getComputedStyle(document.body).color;
        
        function parseRgb(str) {
            const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
            return m ? [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])] : [0,0,0];
        }
        
        function luminance(r, g, b) {
            const a = [r, g, b].map(v => {
                v /= 255;
                return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            });
            return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
        }
        
        const [br, bg, bb] = parseRgb(bodyBg);
        const [cr, cg, cb] = parseRgb(bodyColor);
        const L1 = Math.max(luminance(br, bg, bb), luminance(cr, cg, cb));
        const L2 = Math.min(luminance(br, bg, bb), luminance(cr, cg, cb));
        const ratio = (L1 + 0.05) / (L2 + 0.05);
        
        return { bodyBg, bodyColor, ratio: Math.round(ratio * 10) / 10 };
    }""")
    
    if contrast_check["ratio"] < 4.5:
        findings.append({
            "dimension": "Theming",
            "severity": "P1",
            "desc": f"Low body text contrast ratio: {contrast_check['ratio']}:1 (min 4.5:1 required by WCAG AA)",
            "details": contrast_check
        })

    return overflow_data, contrast_check, findings


def run_comprehensive_audit():
    print("=" * 80)
    print("BIDSAHAYAK IMPECCABLE MULTI-VIEWPORT AUDIT")
    print("=" * 80)

    audit_matrix = []
    all_findings = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        
        for vp in VIEWPORTS:
            print(f"\n>>> Auditing Viewport: {vp['name']} ({vp['width']}x{vp['height']}) - {vp['device']}")
            context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = context.new_page()
            
            console_errors = []
            page.on("pageerror", lambda err: console_errors.append(str(err)))
            
            page.goto("http://127.0.0.1:8000")
            page.wait_for_timeout(600)
            
            # Combinations to test:
            # 1. Light Mode + English
            # 2. Light Mode + Hindi
            # 3. Dark Mode + English
            # 4. Dark Mode + Hindi
            combos = [
                {"theme": "light", "lang": "en"},
                {"theme": "light", "lang": "hi"},
                {"theme": "dark", "lang": "en"},
                {"theme": "dark", "lang": "hi"},
            ]
            
            for combo in combos:
                target_theme = combo["theme"]
                target_lang = combo["lang"]
                
                # Apply theme
                page.evaluate(f"document.documentElement.setAttribute('data-theme', '{target_theme}')")
                # Apply lang
                page.evaluate(f"""() => {{
                    const curLang = document.documentElement.getAttribute('lang') || 'en';
                    if (curLang !== '{target_lang}') {{
                        const btn = document.getElementById('langTgl');
                        if (btn) btn.click();
                    }}
                }}""")
                page.wait_for_timeout(350)
                
                # Check integrity
                oflow, contrast, findings = check_page_integrity(page, vp["name"], target_theme, target_lang)
                
                shot_path = f"shots/impeccable/{vp['name']}_{target_theme}_{target_lang}.png"
                page.screenshot(path=shot_path, full_page=True)
                
                status_str = "PASS" if len(findings) == 0 else f"FLAGGED ({len(findings)} issues)"
                print(f"  [{target_theme.upper()} | {target_lang.upper()}] Overflow: {oflow['diff']}px | Contrast: {contrast['ratio']}:1 -> {status_str}")
                
                audit_matrix.append({
                    "viewport": vp["name"],
                    "width": vp["width"],
                    "height": vp["height"],
                    "theme": target_theme,
                    "lang": target_lang,
                    "overflow_px": oflow["diff"],
                    "contrast_ratio": contrast["ratio"],
                    "screenshot": shot_path,
                    "issues": findings
                })
                
                for f in findings:
                    all_findings.append({
                        "viewport": vp["name"],
                        "theme": target_theme,
                        "lang": target_lang,
                        **f
                    })

            # For standard desktop (1280px), also test interactive flow:
            if vp["width"] == 1280:
                print("  [INTERACTIVE] Testing interactive demo & approval gate at 1280px...")
                run_btn = page.locator("#runDemo")
                if run_btn.count() > 0:
                    run_btn.click()
                    page.wait_for_timeout(4000)
                    
                    # Approve all rows
                    minis = page.locator(".approve-mini")
                    for i in range(minis.count()):
                        minis.nth(i).click()
                        page.wait_for_timeout(50)
                    
                    gate_text = page.locator("#gateCount").inner_text()
                    is_unlocked = page.locator("#genActions").get_attribute("aria-disabled") == "false"
                    print(f"  [INTERACTIVE] Gate result: {gate_text} | Action list unlocked: {is_unlocked}")
                    page.screenshot(path="shots/impeccable/interactive_completed.png")
            
            context.close()
        browser.close()

    summary_file = "shots/impeccable/audit_results.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({"matrix": audit_matrix, "findings": all_findings}, f, indent=2)

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print(f"Total configurations checked: {len(audit_matrix)}")
    print(f"Total unique issues flagged: {len(all_findings)}")
    print(f"Detailed JSON written to: {summary_file}")
    print("=" * 80)

if __name__ == "__main__":
    run_comprehensive_audit()
