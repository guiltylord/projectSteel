import time, ddddocr
from playwright.sync_api import sync_playwright

solver = ddddocr.DdddOcr(show_ad=False)

def force_input(page, sel, val):
    target = page.locator(sel).filter(visible=True).first
    target.wait_for(state="visible")
    target.click()
    target.fill(val)
    page.evaluate("(s) => { const e = document.querySelector(s); if(e) { ['input','change'].forEach(v => e.dispatchEvent(new Event(v, {bubbles:true}))); } }", sel)

def run(plan, data):
    print(f"[*] Запуск Modern Engine для {plan['url']}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(plan['url'], wait_until="domcontentloaded")

        for act in plan['actions']:
            val = data[act['arg_index']] if 'arg_index' in act else ""
            if act['type'] == 'fill':
                force_input(page, act['selector'], val)
            elif act['type'] == 'dropdown':
                page.locator(act['selector']).first.click()
                time.sleep(0.5)
                page.get_by_role("option", name=val).first.click()
                time.sleep(1)
            elif act['type'] == 'click':
                page.locator(act['selector']).filter(visible=True).first.click()
            time.sleep(0.5)

        time.sleep(3)
        if 'captcha' in plan:
            c = plan['captcha']
            try:
                page.wait_for_selector(c['input'], state="visible", timeout=10000)
                img = page.locator(c['image']).filter(visible=True).first
                token = solver.classification(img.screenshot()).strip()
                print(f"   [OCR] {token}")
                page.locator(c['input']).filter(visible=True).fill(token)
                page.locator(c['submit']).filter(visible=True).first.click()
            except: print("   [!] Капча не появилась или уже пройдена")

        time.sleep(5)
        with open("out_modern.html", "w", encoding="utf-8") as f: f.write(page.content())
        browser.close()