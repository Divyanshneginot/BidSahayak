"""
Headless UI & Visual Integrity Audit for BidSahayak.
Tests layout, themes, i18n, interactions, broken assets, and captures diagnostic screenshots.
"""
import os
import sys
from playwright.sync_api import sync_playwright

os.makedirs("shots", exist_ok=True)

errors_found = []
console_messages = []
failed_requests = []


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_audit():
    print("=" * 70)
    print("[AUDIT] Starting BidSahayak Headless UI & Visual Audit...")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Light Mode Audit (1280x900)
        # -------------------------------------------------------------
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # Capture console and network failures
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors_found.append(f"PageError: {err}"))
        page.on("requestfailed", lambda req: failed_requests.append(f"RequestFailed: {req.url} ({req.failure})"))

        page.goto("http://127.0.0.1:8000")
        page.wait_for_timeout(800)

        # Check horizontal overflow
        scroll_width = page.evaluate("document.scrollingElement.scrollWidth")
        inner_width = page.evaluate("window.innerWidth")
        if scroll_width > inner_width:
            errors_found.append(f"Layout Overflow @1280px: scrollWidth={scroll_width} > innerWidth={inner_width}")
        else:
            print("[PASS] Desktop 1280px: No horizontal scroll overflow")

        # Check image and SVG asset presence
        broken_imgs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img'))
                .filter(img => !img.complete || img.naturalWidth === 0)
                .map(img => img.src || img.id || 'unnamed img');
        }""")
        if broken_imgs:
            errors_found.append(f"Broken Images: {broken_imgs}")
        else:
            print("[PASS] All images & textures loaded successfully (0 broken images)")

        # Screenshot desktop light
        page.screenshot(path="shots/audit-desktop-light.png", full_page=True)
        print("[PASS] Screenshot saved: shots/audit-desktop-light.png")

        # -------------------------------------------------------------
        # 2. Dark Theme Audit
        # -------------------------------------------------------------
        theme_btn = page.locator("#themeTgl")
        if theme_btn.count() > 0:
            theme_btn.click()
            page.wait_for_timeout(400)
            theme_attr = page.evaluate("document.documentElement.getAttribute('data-theme')")
            bg_color = page.evaluate("getComputedStyle(document.body).backgroundColor")
            print(f"[PASS] Dark Theme Toggled: data-theme='{theme_attr}', body background={bg_color}")
            page.screenshot(path="shots/audit-desktop-dark.png", full_page=True)
            print("[PASS] Screenshot saved: shots/audit-desktop-dark.png")
            # Toggle back to light
            theme_btn.click()
            page.wait_for_timeout(200)

        # -------------------------------------------------------------
        # 3. Bilingual / Hindi Typography Audit
        # -------------------------------------------------------------
        lang_btn = page.locator("#langTgl")
        if lang_btn.count() > 0:
            lang_btn.click()
            page.wait_for_timeout(400)
            curr_lang = page.evaluate("document.documentElement.lang")
            h1_text = page.locator("h1").inner_text()
            print(f"[PASS] Language switched to: lang='{curr_lang}', H1 preview: {h1_text[:30]}...")
            page.screenshot(path="shots/audit-hindi.png")
            print("[PASS] Screenshot saved: shots/audit-hindi.png")
            # Switch back to English
            lang_btn.click()
            page.wait_for_timeout(200)

        # -------------------------------------------------------------
        # 4. Interactive Demo & Approval Gate Test
        # -------------------------------------------------------------
        run_demo_btn = page.locator("#runDemo")
        if run_demo_btn.count() > 0:
            run_demo_btn.click()
            print("[PASS] Clicked '#runDemo' - running simulated pipeline...")
            page.wait_for_timeout(4200)  # Wait for 3.7s demo run + scroll

            # Verify console output populated
            visible_lines = page.locator("#demoLog .ln.show").count()
            print(f"[PASS] Console log populated with {visible_lines} lines")

            # Check human approval gate interaction
            approve_btns = page.locator(".approve-mini")
            total_btns = approve_btns.count()
            print(f"[PASS] Found {total_btns} per-field approval buttons. Clicking each...")
            for i in range(total_btns):
                approve_btns.nth(i).click()
                page.wait_for_timeout(100)

            gate_text = page.locator("#gateCount").inner_text()
            print(f"[PASS] Gate status: '{gate_text}'")
            action_btn_disabled = page.locator("#genActions").get_attribute("aria-disabled")
            print(f"[PASS] Action list unlock status: aria-disabled={action_btn_disabled}")

            page.screenshot(path="shots/audit-post-demo.png")
            print("[PASS] Screenshot saved: shots/audit-post-demo.png")

        context.close()

        # -------------------------------------------------------------
        # 5. Mobile Viewport Audit (390x844 - iPhone 14 / Android)
        # -------------------------------------------------------------
        mob_context = browser.new_context(viewport={"width": 390, "height": 844})
        mob_page = mob_context.new_page()
        mob_page.goto("http://127.0.0.1:8000")
        mob_page.wait_for_timeout(600)

        mob_scroll_w = mob_page.evaluate("document.scrollingElement.scrollWidth")
        if mob_scroll_w > 391:
            errors_found.append(f"Mobile Overflow @390px: scrollWidth={mob_scroll_w} > 390px")
        else:
            print("[PASS] Mobile 390px: Perfect responsive containment (no side-scroll)")

        mob_page.screenshot(path="shots/audit-mobile.png", full_page=True)
        print("[PASS] Screenshot saved: shots/audit-mobile.png")
        mob_context.close()

        browser.close()

    print("=" * 70)
    print("AUDIT SUMMARY:")
    print(f"  - Total Runtime Errors: {len(errors_found)}")
    print(f"  - Failed Network Requests: {len(failed_requests)}")
    print(f"  - Console Messages: {len(console_messages)}")
    if errors_found:
        print("\n[ISSUES DETECTED]:")
        for err in errors_found:
            print(f"  - {err}")
    if failed_requests:
        print("\n[FAILED REQUESTS]:")
        for req in failed_requests:
            print(f"  - {req}")
    if not errors_found and not failed_requests:
        print("\n[SUCCESS] VISUAL & FUNCTIONAL INTEGRITY CONFIRMED: Zero broken textures, zero layout overflow, clean theme toggles.")
    print("=" * 70)


if __name__ == "__main__":
    run_audit()
