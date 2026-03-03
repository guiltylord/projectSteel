import os
import time
from dotenv import load_dotenv
import ddddocr
from playwright.sync_api import sync_playwright

# Инициализация
load_dotenv()
solver = ddddocr.DdddOcr(show_ad=False)

# Техническая конфигурация (Селекторы и URL)
T_URL = os.getenv("C0")
S_F1 = os.getenv("C1")
S_F2 = os.getenv("C2")
S_F3 = os.getenv("C3")
S_LST = os.getenv("C4")
S_DT = os.getenv("C5")
S_TRG = os.getenv("C6")
S_INP = os.getenv("C7")
S_IMG = os.getenv("C8")
S_TRY = int(os.getenv("C10", "5"))
S_BTN = os.getenv("C11")

# Данные для ввода из окружения
DATA_1 = os.getenv("D1")
DATA_2 = os.getenv("D2")
DATA_3 = os.getenv("D3")
DATA_4 = os.getenv("D4")
DATA_5 = os.getenv("D5")

def start_workflow(v1, v2, v3, v4, v5):
    """
    Запуск универсального процесса обработки формы
    """
    with sync_playwright() as p:
        # Инициализация браузера
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        print("[*] Connection initialization...")
        page.goto(T_URL, wait_until="networkidle")
        
        print(f"[*] Filling primary fields...")
        page.locator(S_F1).fill(v1)
        page.locator(S_F2).fill(v2)
        page.locator(S_F3).fill(v3)

        # Инъекция параметров 
        page.evaluate(f"""
            () => {{
                const elList = document.querySelector('{S_LST}');
                if(elList) {{ 
                    elList.value = '{v5}'; 
                    elList.dispatchEvent(new Event('change', {{ bubbles: true }})); 
                }}
                const elDate = document.querySelector('{S_DT}');
                if(elDate) {{ 
                    elDate.value = '{v4}'; 
                    elDate.dispatchEvent(new Event('change', {{ bubbles: true }})); 
                }}
            }}
        """)

        time.sleep(1)
        page.click(S_TRG)

        status_ok = False
        for i in range(1, S_TRY + 1):
            print(f"[*] Verification attempt #{i}")
            try:
                # Ожидание контейнера верификации
                page.wait_for_selector(S_INP, timeout=8000)
                time.sleep(2)

                img_node = page.query_selector(S_IMG)
                if not img_node:
                    page.reload()
                    continue
                    
                # Обработка графического ключа
                blob = img_node.screenshot()
                token = solver.classification(blob)
                print(f"[>] Token identified: {token}")

                # Ввод и отправка
                page.fill(S_INP, token)
                page.click(S_BTN)
                
                time.sleep(4)

                # Проверка: если инпут пропал, значит успех
                if not page.is_visible(S_INP):
                    print("[+] Verification passed")
                    status_ok = True
                    break
                else:
                    print("[-] Token mismatch, refreshing...")
                    page.click(S_IMG)
                    time.sleep(2)

            except:
                # Если окно исчезло, проверяем наличие результатов на странице
                if "results" in page.content() or "empty" in page.content():
                    status_ok = True
                    break
                break

        if status_ok:
            print("[*] Finalizing data...")
            try:
                page.wait_for_selector('.results, .empty', timeout=10000)
                with open("capture_result.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("[DONE] Content saved to capture_result.html")
            except:
                print("[!] Result containers not found.")
        else:
            print("[FAIL] Workflow interrupted.")

        browser.close()

if __name__ == "__main__":
    # Проверка наличия обязательных данных
    if all([DATA_1, DATA_2, DATA_4, DATA_5]):
        start_workflow(DATA_1, DATA_2, DATA_3, DATA_4, DATA_5)
    else:
        print("Error: Missing input data (D1, D2, D4, D5) in .env configuration.")