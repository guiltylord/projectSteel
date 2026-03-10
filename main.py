# TODO: сделать проверку капчи, так вроде все воркается


import os
import sys
import json
import time
import argparse
import ddddocr
from playwright.sync_api import sync_playwright

# Инициализация OCR
solver = ddddocr.DdddOcr(show_ad=False)

def resolve_locator(page, sel):
    """Превращает кастомные селекторы в локаторы Playwright"""
    if not sel:
        return None
    try:
        if sel.startswith("role:"):
            # Пример: role:button[name='Найти']
            parts = sel.replace("role:", "").split("[name=")
            role = parts[0].strip()
            if len(parts) > 1:
                name = parts[1].replace("]", "").strip().strip("'\"")
                return page.get_by_role(role, name=name)
            return page.get_by_role(role)
            
        elif sel.startswith("placeholder:"):
            text = sel.replace("placeholder:", "").strip()
            return page.get_by_placeholder(text)
            
        elif sel.startswith("text:"):
            text = sel.replace("text:", "").strip()
            return page.get_by_text(text)
            
        # Обычный CSS
        return page.locator(sel)
    except Exception as e:
        print(f"   [!] Ошибка резолвера для '{sel}': {e}")
        return None

def force_input(page, selector, value):
    """Ввод с принудительными событиями для React"""
    if not value: return
    
    target = resolve_locator(page, selector)
    if target is None: return
    
    # Берем первый видимый
    target = target.filter(visible=True).first
    target.wait_for(state="visible", timeout=10000)
    
    target.click()
    target.fill("")
    target.type(str(value), delay=100)
    
    # Пинаем React
    target.evaluate("""(el) => { 
        ['input', 'change', 'blur'].forEach(v => el.dispatchEvent(new Event(v, {bubbles: true}))); 
    }""")

def solve_security(page, cap_cfg):
    """Модуль прохождения капчи"""
    print("   [*] Ожидание окна проверки...")
    
    s_inp = cap_cfg.get('input')
    s_img = cap_cfg.get('image')
    s_sub = cap_cfg.get('submit')
    
    if not s_inp or not s_img or not s_sub:
        print("   [!] Ошибка конфига: не хватает селекторов капчи в JSON.")
        return False

    try:
        # Ждем инпут
        input_loc = resolve_locator(page, s_inp)
        input_loc.first.wait_for(state="visible", timeout=10000)
        time.sleep(1.5)
        
        # Ждем картинку
        img_loc = resolve_locator(page, s_img).filter(visible=True).first
        page.wait_for_function("el => el.src && el.src.length > 10", arg=img_loc.element_handle())
        
        # Скрин и OCR
        img_bytes = img_loc.screenshot()
        token = solver.classification(img_bytes).strip()
        print(f"   [>] OCR Результат: '{token}'")

        if not token: return False

        # Ввод
        force_input(page, s_inp, token)

        # Отправка
        btn_loc = resolve_locator(page, s_sub).filter(visible=True).first
        btn_loc.click()
        
        time.sleep(4)
        
        # Если инпут пропал с экрана - значит капча пройдена
        return not input_loc.first.is_visible()
    except Exception as e:
        print(f"   [!] Ошибка в модуле верификации: {e}")
        return False

def run_engine(scenario_name, input_data):
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
        time.sleep(2)

        # --- ВЫПОЛНЕНИЕ ШАГОВ ---
        for step in cfg.get('actions', []):
            action_type = step['type']
            selector = step['selector']
            
            val = ""
            if 'arg_index' in step:
                idx = step['arg_index']
                val = input_data[idx] if idx < len(input_data) else ""

            try:
                if action_type == 'fill':
                    print(f"[*] Ввод '{val}' в {selector}...")
                    force_input(page, selector, val)
                
                elif action_type == 'click':
                    print(f"[*] Клик по {selector}...")
                    target = resolve_locator(page, selector)
                    if target: target.filter(visible=True).first.click()
                    
                elif action_type == 'press':
                    key_name = step.get('key', 'Enter')
                    print(f"[*] Нажатие клавиши '{key_name}' на {selector}...")
                    target = resolve_locator(page, selector)
                    if target: target.filter(visible=True).first.press(key_name)
                
                time.sleep(1)
            except Exception as e:
                print(f"[!] Ошибка шага {action_type}: {e}")

        # --- КАПЧА ---
        print("\n[*] Проверка состояния защиты...")
        time.sleep(3)
        success = False
        
        if "results" in page.content() or "empty" in page.content():
            print("[*] Результаты доступны без капчи.")
            success = True
        elif 'captcha' in cfg:
            cap_cfg = cfg['captcha']
            for i in range(cap_cfg.get('max_tries', 5)):
                print(f"\n--- Попытка #{i+1} ---")
                if solve_security(page, cap_cfg):
                    success = True
                    break
                
                # Обновление капчи
                try:
                    ref_sel = cap_cfg.get('refresh')
                    if ref_sel:
                        resolve_locator(page, ref_sel).filter(visible=True).first.click()
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

        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Универсальный парсер")
    parser.add_argument("-s", required=True, help="Имя сценария из scenarios.json (например fssp_new)")
    parser.add_argument("-d", nargs='+', default=[], help="Данные по порядку. Пример: -d 'Иванов' 'Москва'")
    
    args = parser.parse_args()
    
    run_engine(args.s, args.d)