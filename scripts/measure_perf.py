import os
import sys
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def measure():
    file_size = os.path.getsize('frontend/index.html')
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        page = await browser.new_page()
        requests = []
        page.on('response', lambda res: requests.append({
            'url': res.url,
            'status': res.status
        }))
        
        t0 = asyncio.get_event_loop().time()
        await page.goto('http://127.0.0.1:8000/', wait_until='networkidle')
        load_time_ms = (asyncio.get_event_loop().time() - t0) * 1000
        
        perf = await page.evaluate('''() => {
            const nav = performance.getEntriesByType('navigation')[0];
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            return {
                domContentLoaded: nav ? nav.domContentLoadedEventEnd : 0,
                load: nav ? nav.loadEventEnd : 0,
                fcp: fcp ? fcp.startTime : 0
            };
        }''')
        
        font_reqs = [r for r in requests if 'font' in r['url'] or 'woff' in r['url']]
        
        print(f"HTML File Size: {file_size / 1024:.1f} KB ({file_size} bytes)")
        print(f"Total Network Requests: {len(requests)}")
        print(f"Font Requests: {len(font_reqs)}")
        print(f"First Contentful Paint (FCP): {perf['fcp']:.1f} ms")
        print(f"DOM Content Loaded: {perf['domContentLoaded']:.1f} ms")
        print(f"Load Event End: {perf['load']:.1f} ms")
        print(f"Total Navigation Wall Time: {load_time_ms:.1f} ms")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(measure())
