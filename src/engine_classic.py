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
                page.evaluate(f"""() => {{
                    const el = document.querySelector('{act['selector']}');
                    if (el) {{
                        el.value = '{val}';
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}""")
            elif act['type'] == 'click':
                page.click(act['selector'])
            time.sleep(0.5)

        time.sleep(2)
        if 'captcha' in plan:
            c = plan['captcha']
            max_tries = c.get('max_tries', 5)
            
            for attempt in range(1, max_tries + 1):
                try:
                    page.wait_for_selector(c['input'], timeout=10000)
                    img = page.query_selector(c['image'])
                    if not img:
                        print("   [!] Не найдено изображение капчи")
                        break
                        
                    token = solver.classification(img.screenshot()).strip()
                    print(f"   [OCR] Попытка #{attempt}: {token}")
                    
                    page.fill(c['input'], token)
                    page.click(c['submit'])
                    time.sleep(3)
                    
                    # Проверяем, исчезло ли окно капчи
                    if not page.is_visible(c['input']):
                        print("   [+] Капча пройдена!")
                        break
                    else:
                        print("   [-] Капча не принята, обновляем...")
                        # Кликаем по картинке для обновления
                        if 'refresh' in c and c['refresh']:
                            page.click(c['refresh'])
                            time.sleep(2)
                            
                except Exception as e:
                    print(f"   [!] Ошибка на попытке #{attempt}: {e}")
                    break

        time.sleep(5)
        with open("out_classic.html", "w", encoding="utf-8") as f: f.write(page.content())
        browser.close()