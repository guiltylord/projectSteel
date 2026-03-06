import os
import time
import ddddocr
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Инициализация окружения и распознавателя
load_dotenv()
solver = ddddocr.DdddOcr(show_ad=False)

# Считывание абстрактной конфигурации из .env
U_TARGET = os.getenv("C20")
S_PRM_INP = os.getenv("C21")
S_LST_INP = os.getenv("C22")
S_PRM_BTN = os.getenv("C23")
S_LST_OPT = os.getenv("C24")
S_MDL_CON = os.getenv("C25")
S_MDL_IMG = os.getenv("C26")
S_MDL_INP = os.getenv("C27")
S_MDL_SUB = os.getenv("C28")
S_MDL_REF = os.getenv("C29")
MAX_TRIES = int(os.getenv("C30", "10"))

# Данные для обработки
V_STR_1 = os.getenv("D21")
V_STR_2 = os.getenv("D22")

def force_input(page, selector, value):
    """
    Заполняет поле и принудительно рассылает 
    события (input, change, blur) для синхронизации с React/Vue.
    """
    target = page.locator(selector).first
    target.wait_for(state="visible")
    target.fill(value)
    # Инъекция JS для мгновенного обновления внутреннего состояния сайта
    page.evaluate(f"""
        (sel) => {{
            const el = document.querySelector(sel);
            if (el) {{
                ['input', 'change', 'blur'].forEach(ev => 
                    el.dispatchEvent(new Event(ev, {{ bubbles: true }}))
                );
            }}
        }}
    """, selector)

def execute_verification(page):
    """Модуль прохождения графического испытания"""
    print("[*] Обработка запроса верификации...")
    try:
        # Ожидание появления контейнера
        page.wait_for_selector(S_MDL_CON, state="visible", timeout=10000)
        
        # Захват и проверка стабильности изображения
        img_node = page.locator(S_MDL_IMG).first
        page.wait_for_function("el => el.src && el.src.length > 10", arg=img_node.element_handle())
        
        # Получение токена
        img_bytes = img_node.screenshot()
        token = solver.classification(img_bytes).strip()
        print(f"   [>] Token: {token}")

        if not token:
            page.locator(S_MDL_REF).first.click()
            return False

        # Ввод токена с использованием форсированного события
        force_input(page, S_MDL_INP, token)

        # Подтверждение
        page.locator(S_MDL_SUB).filter(has_text="Отправить").first.click()
        time.sleep(4)
        
        return not page.is_visible(S_MDL_INP)
    except Exception as e:
        print(f"   [!] Verification module error: {e}")
        return False

def run_workflow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()

        print(f"[*] Connecting to {U_TARGET}...")
        page.goto(U_TARGET, wait_until="networkidle")

        # 1. Ввод первичных строковых данных
        print("[*] Processing primary inputs...")
        force_input(page, S_PRM_INP, V_STR_1)

        # 2. Обработка списков и параметров
        print("[*] Configuring parameters...")
        list_trigger = page.locator(S_LST_INP).first
        list_trigger.click()
        list_trigger.type(V_STR_2, delay=50)
        
        try:
            # Ожидание конкретного элемента в выпадающем списке
            page.wait_for_selector(S_LST_OPT, timeout=5000)
            page.locator(S_LST_OPT).first.click()
        except:
            page.keyboard.press("Enter")

        # 3. Запуск процесса (клик по кнопке поиска)
        print("[*] Triggering main process...")
        page.locator(S_PRM_BTN).filter(has_text="Найти").first.click()

        # 4. Проверка на необходимость верификации
        time.sleep(3)
        status = False
        if "results" in page.content() or "empty" in page.content():
            status = True
        else:
            for attempt in range(MAX_TRIES):
                if execute_verification(page):
                    status = True
                    break
                print(f"   [-] Attempt {attempt+1} failed, retrying...")
                try:
                    page.locator(S_MDL_REF).first.click()
                    time.sleep(2)
                except: pass

        # 5. Сбор и сохранение выходных данных
        if status:
            print("[SUCCESS] Data stream accessed.")
            time.sleep(5)
            with open("workflow_output.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("[DONE] Result saved to workflow_output.html")
        else:
            print("[FAIL] Workflow blocked by security challenge.")

        browser.close()

if __name__ == "__main__":
    run_workflow()