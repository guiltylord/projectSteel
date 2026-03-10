import os
import time
import ddddocr
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
solver = ddddocr.DdddOcr(show_ad=False)

def env(key):
    return os.getenv(key)

# Читаем конфиг
U = env("C20")
S_FIO = env("C21")
S_REG = env("C22")
S_BTN = env("C23")
S_OPT = env("C24")
S_MOD = env("C25")
S_IMG = env("C26")
S_INP = env("C27")
S_SUB = env("C28")
S_REF = env("C29")
MAX_T = int(env("C30") or "5")

def force_input(page, selector, value):
    """Технологичный ввод: клик + печать + события"""
    target = page.locator(selector).filter(visible=True).first
    target.wait_for(state="visible", timeout=10000)
    target.click()
    target.fill("")
    target.type(value, delay=50)
    # Принудительный вызов событий для React
    page.evaluate(f"()=>{{const e=document.querySelector('{selector}'); if(e){{e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));}}}}")

def solve_security(page):
    """Модуль прохождения капчи"""
    print("   [*] Ожидание окна проверки...")
    try:
        # Ждем именно видимый инпут капчи
        page.wait_for_selector(S_INP, state="visible", timeout=10000)
        time.sleep(1.5)
        
        # Находим картинку
        img_node = page.locator(S_IMG).filter(visible=True).first
        # Проверяем, что картинка загружена
        page.wait_for_function("el => el.src && el.src.length > 10", arg=img_node.element_handle())
        
        img_bytes = img_node.screenshot()
        token = solver.classification(img_bytes).strip()
        print(f"   [>] OCR Результат: {token}")

        if not token: return False

        # Ввод в видимое поле
        force_input(page, S_INP, token)

        # Жмем "Отправить" внутри модалки
        page.locator(S_SUB).filter(has_text="Отправить").filter(visible=True).first.click()
        
        time.sleep(4)
        return not page.is_visible(S_INP)
    except Exception as e:
        print(f"   [!] Ошибка в модуле верификации: {e}")
        return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()

        print(f"[*] Переход на {U}...")
        # Используем commit вместо networkidle, чтобы не ждать вечно
        page.goto(U, wait_until="domcontentloaded")
        page.wait_for_selector(S_FIO, timeout=20000)

        # 1. Заполняем ФИО
        print("[*] Заполнение ФИО...")
        force_input(page, S_FIO, env("D21"))

        # 2. Регион
        print("[*] Выбор региона...")
        reg_input = page.locator(S_REG).first
        reg_input.click()
        reg_input.type(env("D22"), delay=100)
        
        try:
            # Ждем именно строку в списке
            page.wait_for_selector(S_OPT, state="visible", timeout=5000)
            page.locator(S_OPT).first.click()
            print("      [v] Регион выбран.")
        except:
            page.keyboard.press("Enter")

        # 3. Кнопка Найти
        print("[*] Поиск...")
        page.locator(S_BTN).filter(has_text="Найти").first.click()

        # 4. Цикл капчи
        time.sleep(2)
        success = False
        if "results" in page.content() or "empty" in page.content():
            success = True
        else:
            for i in range(MAX_T):
                print(f"\n--- Попытка #{i+1} ---")
                if solve_security(page):
                    success = True
                    break
                # Если не прошло - жмем Обновить
                try:
                    page.locator(S_REF).first.click()
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
    run()