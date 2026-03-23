import os
import json
import time
import argparse
import ddddocr
from playwright.sync_api import sync_playwright

solver = ddddocr.DdddOcr(show_ad=False)

def resolve_locator(page, selector_str):
    """Превращает строку-инструкцию в объект Playwright"""
    if not selector_str:
        return None
    try:
        if selector_str.startswith("role:"):
            parts = selector_str.replace("role:", "").split("[name=")
            role = parts[0]
            name = parts[1].replace("]", "") if len(parts) > 1 else None
            return page.get_by_role(role, name=name).filter(visible=True).first
        if selector_str.startswith("placeholder:"):
            text = selector_str.replace("placeholder:", "")
            return page.get_by_placeholder(text).filter(visible=True).first
        if selector_str.startswith("text:"):
            text = selector_str.replace("text:", "")
            return page.get_by_text(text).filter(visible=True).first

        return page.locator(selector_str).filter(visible=True).first
    except:
        return page.locator(selector_str).first

def force_input(page, selector_str, value):
    """Технологичный ввод: клик + печать + события"""
    if not value: return
    target = resolve_locator(page, selector_str)
    target.wait_for(state="visible", timeout=10000)
    target.click()
    target.fill("")
    target.type(str(value), delay=50)
    page.evaluate(f"()=>{{const e=document.querySelector('{selector_str}'); if(e){{e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));}}}}")

def solve_security(page, config):
    """Модуль прохождения капчи"""
    print("   [*] Ожидание окна проверки...")
    
    # Берем селекторы прямо из JSON конфига капчи
    s_mod = config.get('modal')
    s_img = config.get('image')
    s_inp = config.get('input')
    s_sub = config.get('submit')
    
    if not s_inp or not s_img or not s_sub:
        print("   [!] Ошибка конфига: не хватает селекторов капчи.")
        return False

    try:
        page.wait_for_selector(s_inp, state="visible", timeout=10000)
        time.sleep(1.5)
        
        img_node = page.locator(s_img).filter(visible=True).first
        page.wait_for_function("el => el.src && el.src.length > 10", arg=img_node.element_handle())
        
        img_bytes = img_node.screenshot()
        token = solver.classification(img_bytes).strip()
        print(f"   [>] OCR Результат: {token}")

        if not token: return False

        force_input(page, s_inp, token)
        resolve_locator(page, s_sub).click()
        
        time.sleep(4)
        return not page.is_visible(s_inp)
    except Exception as e:
        print(f"   [!] Ошибка в модуле верификации: {e}")
        return False

def run_engine(scenario_name, input_data):
    if not os.path.exists("scenarios.json"):
        print("[!] Ошибка: scenarios.json не найден")
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

        # --- ВЫПОЛНЕНИЕ ШАГОВ ИЗ JSON ---
        for step in cfg.get('actions', []):
            typ = step['type']
            sel = step['selector']
            
            # Подставляем данные юзера из консоли
            val = ""
            if 'arg_index' in step:
                idx = step['arg_index']
                val = input_data[idx] if idx < len(input_data) else ""

            print(f"[*] Task: {typ} -> {sel}")
            try:
                if typ == 'force_fill':
                    force_input(page, sel, val)
                elif typ == 'click':
                    resolve_locator(page, sel).click()
                elif typ == 'dropdown':
                    trigger = resolve_locator(page, sel)
                    trigger.click()
                    trigger.type(val, delay=100)
                    opt_sel = step.get('opt_selector')
                    page.wait_for_selector(opt_sel, state="visible", timeout=5000)
                    page.locator(opt_sel).first.click()
                time.sleep(1)
            except Exception as e:
                print(f"   [!] Пропущено: {e}")

        # --- КАПЧА ---
        print("\n[*] Проверка состояния защиты...")
        status = False
        time.sleep(2)
        
        if "results" in page.content() or "empty" in page.content():
            status = True
        elif 'captcha' in cfg:
            cap_cfg = cfg['captcha']
            max_tries = cap_cfg.get('max_tries', 5)
            for i in range(max_tries):
                print(f"\n--- Проверка капчи #{i+1} ---")
                if solve_security(page, cap_cfg):
                    status = True
                    break
                try:
                    ref_sel = cap_cfg.get('refresh')
                    if ref_sel:
                        resolve_locator(page, ref_sel).click()
                        time.sleep(2)
                except: pass

        if status:
            print("\n[SUCCESS] Данные получены!")
            time.sleep(5)
            with open("out.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("[DONE] Сохранено в out.html")
        else:
            print("\n[FAIL] Не удалось пройти защиту.")

        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Scraper")
    parser.add_argument("-s", required=True, help="Имя сценария из JSON")
    # nargs='+' позволяет передавать много строк: "Иванов" "Москва"
    parser.add_argument("-d", nargs='+', default=[], help="Данные на вход через пробел")
    
    args = parser.parse_args()
    run_engine(args.s, args.d)