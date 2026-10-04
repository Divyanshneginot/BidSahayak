import asyncio
from playwright.async_api import async_playwright

async def baseline():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        # Fresh load: no localStorage
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        
        # 1. Check data-theme and root computed styles on fresh load in light mode
        has_theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        # Check computed color of .status.met on fresh load
        met_color = await page.evaluate("""() => {
            const el = document.querySelector('.status.met');
            return window.getComputedStyle(el).color;
        }""")
        print(f"Baseline fresh load: data-theme={has_theme}, .status.met color={met_color}")
        
        # 2. Check demo reconciliation text
        vm_text = await page.evaluate("""() => {
            const el = document.querySelectorAll('.vm b')[1];
            return el ? el.innerText : '';
        }""")
        why_text = await page.evaluate("""() => {
            const el = document.querySelector('.verdict-why');
            return el ? el.innerText : '';
        }""")
        print(f"Baseline VM text: '{vm_text}', why: '{why_text}'")

        # 3. Test language toggle in light mode
        await page.click("#langTgl")
        await page.wait_for_timeout(300)
        hi_lang = await page.evaluate("document.documentElement.getAttribute('lang')")
        print(f"After lang toggle: lang={hi_lang}")

        # 4. Mobile viewport 360px check
        await page.set_viewport_size({"width": 360, "height": 740})
        nav_display = await page.evaluate("""() => {
            const nav = document.querySelector('nav.main');
            const links = Array.from(nav.querySelectorAll('a')).map(a => ({
                text: a.innerText,
                display: window.getComputedStyle(a).display
            }));
            return links;
        }""")
        print(f"Baseline 360px nav links: {nav_display}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(baseline())
