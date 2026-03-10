import os
import sys
import json
import time
import argparse
import ddddocr
from playwright.sync_api import sync_playwright

# Инициализация OCR
solver = ddddocr.DdddOcr(show_ad=False)

def force_input(page, selector, value):
    """Технологичный ввод: клик + печать + события"""
    if not value: return
    target = page.locator(selector).filter(visible=True).first
    target.wait_for(state="visible", timeout=10000)
    target.click()
    target.fill("")
    target.type(str(value), delay=50)
    # Принудительный вызов событий для React
    page.evaluate(f"()=>{{const e=document.querySelector('{selector}'); if(e){{e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));}}}}")

def solve_security(page, cap_cfg):
    """Модуль прохождения капчи"""
    print("   [*] Ожидание окна проверки...")
    try:
        # Ждем именно видимый инпут капчи
        page.wait_for_selector(cap_cfg['input'], state="visible", timeout=10000)
        time.sleep(1.5)
        
        # Находим картинку
        img_node = page.locator(cap_cfg['image']).filter(visible=True).first
        page.wait_for_function("el => el.src && el.src.length > 10", arg=img_node.element_handle())
        
        img_bytes = img_node.screenshot()
        token = solver.classification(img_bytes).strip()
        print(f"   [>] OCR Результат: {token}")

        if not token: return False

        # Ввод в видимое поле
        force_input(page, cap_cfg['input'], token)

        # Жмем "Отправить" внутри модалки
        page.locator(cap_cfg['submit']).filter(has_text="Отправить").filter(visible=True).first.click()
        
        time.sleep(4)
        return not page.is_visible(cap_cfg['input'])
    except Exception as e:
        print(f"   [!] Ошибка в модуле верификации: {e}")
        return False

def run_engine(scenario_name, input_data):
    """
    scenario_name: имя ключа из JSON (напр. fssp_new)
    input_data: список строк (напр. ["Абакумов...", "Москва"])
    """
    if not os.path.exists("scenarios.json"):
        print("[!] Файл scenarios.json не найден!")
        return

    with open("scenarios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if scenario_name not in data:
        print(f"[!] Сценарий '{scenario_name}' не найден в JSON!")
        return

    cfg = data[scenario_name]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()

        print(f"[*] Переход на {cfg['url']}...")
        page.goto(cfg['url'], wait_until="domcontentloaded")

        # --- ВЫПОЛНЕНИЕ ШАГОВ ---
        for step in cfg.get('actions', []):
            action_type = step['type']
            selector = step['selector']
            
            # Извлекаем данные из массива консоли по индексу
            val = ""
            if 'arg_index' in step:
                idx = step['arg_index']
                val = input_data[idx] if idx < len(input_data) else ""

            try:
                if action_type == 'fill':
                    print(f"[*] Ввод '{val}' в {selector}...")
                    force_input(page, selector, val)
                
                elif action_type == 'dropdown':
                    print(f"[*] Выбор '{val}' в списке {selector}...")
                    reg_input = page.locator(selector).first
                    reg_input.click()
                    reg_input.type(val, delay=100)
                    try:
                        opt_sel = step['opt_selector']
                        page.wait_for_selector(opt_sel, state="visible", timeout=5000)
                        page.locator(opt_sel).first.click()
                    except:
                        page.keyboard.press("Enter")
                
                elif action_type == 'click':
                    print(f"[*] Клик по {selector}...")
                    page.locator(selector).first.click()
                
                time.sleep(1)
            except Exception as e:
                print(f"[!] Ошибка шага: {e}")

        # --- КАПЧА ---
        time.sleep(2)
        success = False
        if "results" in page.content() or "empty" in page.content():
            success = True
        elif 'captcha' in cfg:
            cap = cfg['captcha']
            for i in range(cap.get('max_tries', 5)):
                print(f"\n--- Попытка #{i+1} ---")
                if solve_security(page, cap):
                    success = True
                    break
                try:
                    page.locator(cap['refresh']).first.click()
                    time.sleep(2)
                except: pass

        # --- ИТОГ ---
        if success:
            print("\n[SUCCESS] Данные получены!")
            time.sleep(5)
            with open("out.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("[DONE] Сохранено в out.html")
        else:
            print("\n[FAIL] Не удалось пробиться.")

        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Универсальный парсер")
    parser.add_argument("-s", required=True, help="Имя сценария из scenarios.json")
    parser.add_argument("-d", nargs='+', default=[], help="Данные по порядку. Пример: -d 'Иванов' 'Москва'")
    
    args = parser.parse_args()
    
    run_engine(args.s, args.d)