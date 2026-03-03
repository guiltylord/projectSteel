import os
import time
import ddddocr
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
solver = ddddocr.DdddOcr(show_ad=False)

# Абстрактные ключи
U = os.getenv("C0")  
S1 = os.getenv("C1") 
S2 = os.getenv("C2") 
S3 = os.getenv("C3") 
S4 = os.getenv("C4") 
S5 = os.getenv("C5") # Модалка
S6 = os.getenv("C6") # Картинка
S7 = os.getenv("C7") # Инпут кода
S8 = os.getenv("C8") # Кнопка Отправить
S9 = os.getenv("C9") # Кнопка Обновить
MAX_T = int(os.getenv("C10", "10"))

def process_challenge(page):
    print("\n[DEBUG] Ищу окно верификации...")
    try:
        # 1. Ждем модалку
        page.wait_for_selector(S5, state="visible", timeout=10000)
        
        # 2. Ищем картинку агрессивно
        # Сначала пробуем твой селектор, если нет - любую картинку в модалке
        img_node = page.locator(S5).locator("img").first
        
        # Ждем, пока у картинки появится нормальный src (не пустой)
        page.wait_for_function(
            "el => el.src && el.src.length > 10", 
            arg=img_node.element_handle(),
            timeout=5000
        )

        # Делаем скриншот
        img_bytes = img_node.screenshot()
        with open("captured.png", "wb") as f:
            f.write(img_bytes)
        
        if len(img_bytes) < 500:
            print("[!] Скриншот слишком маленький, что-то не так.")
            return False

        # 3. Распознаем
        token = solver.classification(img_bytes).strip()
        print(f"[>] Результат распознавания: '{token}'")

        if not token:
            print("[!] Код не распознан. Жму обновить...")
            page.locator(S9).first.click()
            time.sleep(2)
            return False

        # 4. Ввод
        print(f"[*] Ввожу код в поле...")
        inp = page.locator(S7).filter(visible=True).first
        inp.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        inp.type(token, delay=100)

        # 5. Клик Отправить
        print("[*] Нажимаю кнопку подтверждения...")
        page.locator(S8).filter(has_text="Отправить").first.click()
        
        time.sleep(4)
        
        # Если модалка пропала - победа
        if not page.is_visible(S5):
            return True
        else:
            print("[-] Код не подошел. Обновляю...")
            page.locator(S9).first.click()
            time.sleep(2)
            return False
            
    except Exception as e:
        print(f"[!] Ошибка в модуле верификации: {e}")
        # На всякий случай проверим, может мы уже зашли
        if "results" in page.content() or "empty" in page.content():
            return True
        return False

def run_workflow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = context.new_page()

        print(f"[*] Целевой URL: {U}")
        page.goto(U, wait_until="networkidle")

        # 1. ФИО
        print("[*] Ввод первичных данных...")
        page.locator(S1).first.type(os.getenv("D1"), delay=60)

        # 2. Регион
        print("[*] Настройка параметров...")
        lst = page.locator(S2).first
        lst.click()
        lst.type(os.getenv("D5"), delay=100)
        
        try:
            page.wait_for_selector(S4, timeout=5000)
            page.locator(S4).first.click()
        except:
            page.keyboard.press("Enter")

        time.sleep(1)

        # 3. Триггер поиска
        print("[*] Запуск процесса...")
        page.locator(S3).filter(has_text="Найти").first.click()

        # 4. Прохождение проверок
        success = False
        time.sleep(3)
        
        if "results" in page.content() or "empty" in page.content():
            success = True
        else:
            for i in range(MAX_T):
                print(f"\n--- Попытка #{i+1} ---")
                if process_challenge(page):
                    success = True
                    break

        if success:
            print("\n[SUCCESS] Процесс завершен.")
            time.sleep(5)
            with open("output_final.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("[DONE] Данные в output_final.html")
        else:
            print("\n[FAIL] Верификация не пройдена.")

        browser.close()

if __name__ == "__main__":
    run_workflow()