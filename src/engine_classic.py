import time, ddddocr
from playwright.sync_api import sync_playwright

solver = ddddocr.DdddOcr(show_ad=False)

def run(plan, data):
    print(f"[*] Запуск Classic Engine для {plan['url']}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(plan['url'])

        for act in plan['actions']:
            val = data[act['arg_index']] if 'arg_index' in act else ""
            if act['type'] == 'fill':
                page.locator(act['selector']).fill(val)
            elif act['type'] == 'js_inject':
                page.evaluate(f"()=>{{document.querySelector('{act['selector']}').value='{val}';}}")
            elif act['type'] == 'click':
                page.click(act['selector'])
            time.sleep(0.5)

        time.sleep(2)
        if 'captcha' in plan:
            c = plan['captcha']
            page.wait_for_selector(c['input'])
            img = page.query_selector(c['image'])
            token = solver.classification(img.screenshot()).strip()
            print(f"   [OCR] {token}")
            page.fill(c['input'], token)
            page.click(c['submit'])

        time.sleep(5)
        with open("out_classic.html", "w", encoding="utf-8") as f: f.write(page.content())
        browser.close()