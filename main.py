import os
import json
import time
import ddddocr
from playwright.sync_api import sync_playwright

# Инициализация OCR
solver = ddddocr.DdddOcr(show_ad=False)

def force_input(page, selector, value):
    """Технологичный ввод: клик + печать + события"""
    target = page.locator(selector).filter(visible=True).first
    target.wait_for(state="visible", timeout=10000)
    target.click()
    target.fill("")
    target.type(value, delay=50)
    # Принудительный вызов событий для React
    page.evaluate(f"()=>{{const e=document.querySelector('{selector}'); if(e){{e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));}}}}")

def solve_security(page, captcha_cfg):
    """Модуль прохождения капчи"""
    print("   [*] Ожидание окна проверки...")
    try:
        # Ждем именно видимый инпут капчи
        page.wait_for_selector(captcha_cfg['input'], state="visible", timeout=10000)
        time.sleep(1.5)
        
        # Находим картинку
        img_node = page.locator(captcha_cfg['image']).filter(visible=True).first
        # Проверяем, что картинка загружена
        page.wait_for_function("el => el.src && el.src.length > 10", arg=img_node.element_handle())
        
        img_bytes = img_node.screenshot()
        token = solver.classification(img_bytes).strip()
        print(f"   [>] OCR Результат: {token}")

        if not token: return False

        # Ввод в видимое поле
        force_input(page, captcha_cfg['input'], token)

        # Жмем "Отправить" внутри модалки
        page.locator(captcha_cfg['submit']).filter(has_text="Отправить").filter(visible=True).first.click()
        
        time.sleep(4)
        return not page.is_visible(captcha_cfg['input'])
    except Exception as e:
        print(f"   [!] Ошибка в модуле верификации: {e}")
        return False

def run_scenario(scenario_name):
    # Читаем конфиг из JSON
    if not os.path.exists("scenarios.json"):
        print("[!] Файл scenarios.json не найден!")
        return

    with open("scenarios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if scenario_name not in data:
        print(f"[!] Сценарий {scenario_name} не найден в JSON!")
        return

    cfg = data[scenario_name]
    sel = cfg['selectors']
    inp = cfg['inputs']
    cap = cfg['captcha']

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()

        print(f"[*] Переход на {cfg['url']}...")
        page.goto(cfg['url'], wait_until="domcontentloaded")
        page.wait_for_selector(sel['fio_field'], timeout=20000)

        # 1. Заполняем ФИО
        print("[*] Заполнение ФИО...")
        force_input(page, sel['fio_field'], inp['fio'])

        # 2. Регион
        print("[*] Выбор региона...")
        reg_input = page.locator(sel['region_field']).first
        reg_input.click()
        reg_input.type(inp['region'], delay=100)
        
        try:
            # Ждем именно строку в списке
            page.wait_for_selector(sel['region_option'], state="visible", timeout=5000)
            page.locator(sel['region_option']).first.click()
            print("      [v] Регион выбран.")
        except:
            page.keyboard.press("Enter")

        # 3. Кнопка Найти
        print("[*] Поиск...")
        page.locator(sel['search_btn']).filter(has_text="Найти").first.click()

        # 4. Цикл капчи
        time.sleep(2)
        success = False
        if "results" in page.content() or "empty" in page.content():
            success = True
        else:
            for i in range(cap['max_tries']):
                print(f"\n--- Попытка #{i+1} ---")
                if solve_security(page, cap):
                    success = True
                    break
                # Если не прошло - жмем Обновить
                try:
                    page.locator(cap['refresh']).first.click()
                    time.sleep(2)
                except: pass

        # 5. Итог
        if success:
            print("\n[SUCCESS] Данные получены!")
            time.sleep(5)
            try:
                with open("out.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("[DONE] Сохранено в out.html")
            except Exception as e:
                print(f"[!] Ошибка сохранения: {e}")
        else:
            print("\n[FAIL] Не удалось пробиться.")

        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    # Вызываем нужный блок из JSON
    run_scenario("fssp_new")