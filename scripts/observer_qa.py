import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "shots", "qa")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

findings = []

def record(test_name, passed, detail):
    status = "PASS" if passed else "FAIL"
    findings.append({"test": test_name, "status": status, "detail": detail})
    print(f"[{status}] {test_name}: {detail}")

async def run_observer_qa():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        
        # Collect console errors
        console_errors = []
        
        # ---------------------------------------------------------------------
        # TEST 1: Fresh Load in Light Mode (Priority 3 & 1)
        # ---------------------------------------------------------------------
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            color_scheme="light"
        )
        page = await context.new_page()
        page.on("pageerror", lambda err: console_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(400)
        
        # Check data-theme attribute on fresh load
        data_theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        record("Fresh load data-theme", data_theme is None, f"data-theme is {data_theme} (correctly unset on fresh light load)")
        
        # Check status met color (must not bleed dark-mode color)
        met_color = await page.evaluate("window.getComputedStyle(document.querySelector('.status.met')).color")
        is_light_green = "rgb(46, 90, 18)" in met_color or "rgb(54, 94, 20)" in met_color
        record("Status met light color", is_light_green, f"Computed color: {met_color} (dark bleed eliminated)")
        
        # Check verdict kicker color token
        kicker_color = await page.evaluate("window.getComputedStyle(document.querySelector('.verdict-band .mono')).color")
        record("Verdict kicker color token", "rgb(110, 110, 110)" in kicker_color, f"Computed kicker color: {kicker_color}")
        
        # Check focus indicator contrast
        focus_outline = await page.evaluate("""() => {
            const btn = document.querySelector('#runDemo');
            btn.focus();
            const s = window.getComputedStyle(btn);
            return { outline: s.outline, boxShadow: s.boxShadow };
        }""")
        record("Focus indicator styling", bool(focus_outline.get("outline")), f"Focus styles: {focus_outline}")
        
        # Check reconciled counts
        vm_text = await page.evaluate("document.querySelectorAll('.verdict-meta .vm b')[1].innerText")
        record("Reconciled verdict count", vm_text == "1+1/6", f"Meta counter shows: '{vm_text}' (expected 1+1/6)")
        
        why_text = await page.evaluate("document.querySelector('.verdict-why').innerText")
        record("Verdict explanation reconciled", "1 requirement outright" in why_text and "1+1 of 6" in why_text, f"Summary: '{why_text}'")
        
        trace_stat = await page.evaluate("document.querySelectorAll('.tcell .t-stat')[3].innerText")
        record("Trace cell 4 reconciled", "met 1" in trace_stat and "exempt 1" in trace_stat, f"Trace stat: '{trace_stat}'")

        # Screenshots
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "full_fresh_light.png"), full_page=True)
        hero = page.locator("#top")
        await hero.screenshot(path=os.path.join(SCREENSHOT_DIR, "hero_light.png"))
        result = page.locator("#result")
        await result.screenshot(path=os.path.join(SCREENSHOT_DIR, "result_light.png"))
        
        # ---------------------------------------------------------------------
        # TEST 2: Theme Toggle to Dark Mode (Priority 3)
        # ---------------------------------------------------------------------
        await page.click("#themeTgl")
        await page.wait_for_timeout(300)
        dark_theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        record("Theme toggle sets dark", dark_theme == "dark", f"data-theme={dark_theme}")
        
        dark_met_color = await page.evaluate("window.getComputedStyle(document.querySelector('.status.met')).color")
        is_dark_green = "rgb(134, 239, 172)" in dark_met_color
        record("Status met dark color", is_dark_green, f"Dark status met color: {dark_met_color}")
        
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "full_dark.png"), full_page=True)
        await hero.screenshot(path=os.path.join(SCREENSHOT_DIR, "hero_dark.png"))
        await result.screenshot(path=os.path.join(SCREENSHOT_DIR, "result_dark.png"))

        # ---------------------------------------------------------------------
        # TEST 3: Language Toggle (EN <-> HI)
        # ---------------------------------------------------------------------
        await page.click("#themeTgl") # back to light
        await page.wait_for_timeout(200)
        await page.click("#langTgl")
        await page.wait_for_timeout(300)
        
        lang_val = await page.evaluate("document.documentElement.getAttribute('lang')")
        record("Lang toggle sets hi", lang_val == "hi", f"lang attribute: {lang_val}")
        
        hi_title = await page.evaluate("document.querySelector('h1.hero-title').innerText")
        record("Hindi hero title translated", "बोली लगा सकता हूँ" in hi_title, f"Hindi title: {hi_title[:40]}...")
        
        # Check Devanagari letter-spacing
        hi_ls = await page.evaluate("window.getComputedStyle(document.querySelector('h1.hero-title')).letterSpacing")
        record("Devanagari letter-spacing zeroed", hi_ls in ("0px", "normal"), f"Heading letter-spacing: {hi_ls}")
        
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "hero_hindi.png"))
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "result_hindi.png"))

        # Toggle back to English
        await page.click("#langTgl")
        await page.wait_for_timeout(300)
        en_lang = await page.evaluate("document.documentElement.getAttribute('lang')")
        record("Lang toggle restores en", en_lang == "en", f"lang attribute: {en_lang}")

        # ---------------------------------------------------------------------
        # TEST 4: Viewports & Mobile Menu (360, 390, 768, 1024, 1440)
        # ---------------------------------------------------------------------
        viewports = [
            ("mobile_360", 360, 740),
            ("mobile_390", 390, 844),
            ("tablet_768", 768, 1024),
            ("laptop_1024", 1024, 768),
            ("desktop_1440", 1440, 900)
        ]
        
        for name, w, h in viewports:
            await page.set_viewport_size({"width": w, "height": h})
            await page.wait_for_timeout(250)
            
            overflow = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            record(f"Viewport {w}px overflow check", not overflow, f"Width {w}px has overflow: {overflow}")
            
            if w <= 860:
                # Test mobile menu toggle button visibility & size
                menu_btn_info = await page.evaluate("""() => {
                    const btn = document.querySelector('#menuTgl');
                    const rect = btn.getBoundingClientRect();
                    const s = window.getComputedStyle(btn);
                    return { display: s.display, width: rect.width, height: rect.height };
                }""")
                meets_tap_target = menu_btn_info["width"] >= 44 and menu_btn_info["height"] >= 44
                record(f"Mobile menu button at {w}px", menu_btn_info["display"] != "none" and meets_tap_target,
                       f"Display: {menu_btn_info['display']}, Target: {menu_btn_info['width']}x{menu_btn_info['height']}px")
                
                # Test opening mobile menu
                await page.click("#menuTgl")
                await page.wait_for_timeout(200)
                nav_open = await page.evaluate("document.querySelector('#mainNav').classList.contains('open')")
                aria_exp = await page.evaluate("document.querySelector('#menuTgl').getAttribute('aria-expanded')")
                record(f"Mobile menu open at {w}px", nav_open and aria_exp == "true", f"Nav open: {nav_open}, aria-expanded={aria_exp}")
                
                if w == 360:
                    await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_360_nav_open.png"))
                
                # Test Escape key closes menu and focuses toggle
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(200)
                nav_closed = await page.evaluate("!document.querySelector('#mainNav').classList.contains('open')")
                active_id = await page.evaluate("document.activeElement.id")
                record(f"Escape closes mobile menu at {w}px", nav_closed and active_id == "menuTgl",
                       f"Nav closed: {nav_closed}, focused element: #{active_id}")

        # Reset to desktop viewport
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.wait_for_timeout(200)

        # ---------------------------------------------------------------------
        # TEST 5: Upload Client Validation
        # ---------------------------------------------------------------------
        # Invalid file upload (not PDF)
        await page.evaluate("""() => {
            const dt = new DataTransfer();
            const file = new File(["fake text content"], "sample.txt", {type: "text/plain"});
            dt.items.add(file);
            const fi = document.querySelector("#fileInput");
            fi.files = dt.files;
            fi.dispatchEvent(new Event("change", {bubbles: true}));
        }""")
        await page.wait_for_timeout(250)
        feedback_err = await page.evaluate("""() => {
            const fb = document.querySelector("#uploadFeedback");
            return { display: fb.style.display, text: fb.innerText };
        }""")
        record("Upload non-PDF validation", feedback_err["display"] == "block" and "Invalid file format" in feedback_err["text"],
               f"Feedback: {feedback_err}")

        # ---------------------------------------------------------------------
        # TEST 6: Demo Run & prefers-reduced-motion
        # ---------------------------------------------------------------------
        # Normal demo run
        await page.click("#runDemo")
        await page.wait_for_timeout(1000)
        timer_text = await page.evaluate("document.querySelector('#demoTimer').innerText")
        record("Normal demo timer active", "s" in timer_text, f"Timer during demo: {timer_text}")
        await page.wait_for_timeout(3000)
        final_timer = await page.evaluate("document.querySelector('#demoTimer').innerText")
        record("Normal demo completion", "illustrative" in final_timer, f"Final demo timer: {final_timer}")

        # Reduced motion context
        rm_context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            reduced_motion="reduce"
        )
        rm_page = await rm_context.new_page()
        await rm_page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await rm_page.click("#runDemo")
        await rm_page.wait_for_timeout(150)
        rm_timer = await rm_page.evaluate("document.querySelector('#demoTimer').innerText")
        rm_done = await rm_page.evaluate("document.querySelector('#demoBar').classList.contains('done')")
        record("Reduced motion instant completion", rm_done and "illustrative" in rm_timer, f"Reduced motion timer: {rm_timer}, done: {rm_done}")
        await rm_context.close()

        # ---------------------------------------------------------------------
        # TEST 7: Approval Gate
        # ---------------------------------------------------------------------
        is_initially_locked = await page.evaluate("document.querySelector('#genActions').getAttribute('aria-disabled') === 'true'")
        record("Approval gate initially locked", is_initially_locked, f"aria-disabled={is_initially_locked}")
        
        # Click all 6 approve buttons
        approve_count = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('.approve-mini'));
            btns.forEach(b => b.click());
            return btns.length;
        }""")
        await page.wait_for_timeout(200)
        unlocked = await page.evaluate("document.querySelector('#genActions').getAttribute('aria-disabled') === 'false'")
        gate_txt = await page.evaluate("document.querySelector('#gateCount').innerText")
        record("Approval gate unlocks at 6/6", unlocked and "6 / 6" in gate_txt, f"Gate text: {gate_txt}, unlocked: {unlocked}")
        
        # Click generate action list
        await page.click("#genActions")
        await page.wait_for_timeout(300)
        action_wrap_locked = await page.evaluate("document.querySelector('#actionWrap').classList.contains('locked')")
        record("Action list unlocked", not action_wrap_locked, f"Action wrap locked: {action_wrap_locked}")

        # ---------------------------------------------------------------------
        # Console Errors check
        # ---------------------------------------------------------------------
        # Filter out external font network failures if any
        actual_errors = [e for e in console_errors if "font" not in e.lower() and "favicon" not in e.lower()]
        record("Zero JS Console Errors", len(actual_errors) == 0, f"Errors: {actual_errors}")

        await browser.close()
        return findings

if __name__ == "__main__":
    asyncio.run(run_observer_qa())
