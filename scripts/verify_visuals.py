import os
from playwright.sync_api import sync_playwright

os.makedirs("shots/verified", exist_ok=True)

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="msedge", headless=True)
    except Exception:
        browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

    # 1. Light Mode - Hero
    page.screenshot(path="shots/verified/01_hero_light_en.png", clip={"x": 0, "y": 0, "width": 1280, "height": 700})
    
    # 2. Toggle to Hindi
    page.click("#langTgl")
    page.wait_for_timeout(300)
    page.screenshot(path="shots/verified/02_hero_light_hi.png", clip={"x": 0, "y": 0, "width": 1280, "height": 700})
    
    # Back to English
    page.click("#langTgl")
    page.wait_for_timeout(300)

    # 3. Light Mode - Result & Verdict
    res = page.locator("#result")
    res.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    page.screenshot(path="shots/verified/03_verdict_light.png")

    # 4. Light Mode - Source View
    src = page.locator("#source")
    src.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    page.screenshot(path="shots/verified/04_source_light.png")

    # 5. Light Mode - Trace & Confidence
    trace = page.locator("#trace")
    trace.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    page.screenshot(path="shots/verified/05_trace_light.png")

    # 6. Dark Mode - Toggle Dark
    page.click("#themeTgl")
    page.wait_for_timeout(400)

    # 7. Dark Mode - Hero
    page.locator("#top").scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.screenshot(path="shots/verified/06_hero_dark.png", clip={"x": 0, "y": 0, "width": 1280, "height": 700})

    # 8. Dark Mode - Verdict
    res.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.screenshot(path="shots/verified/07_verdict_dark.png")

    browser.close()

print("Visual verification screenshots saved to shots/verified/")
