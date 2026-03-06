import os
import time
import ddddocr
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
solver = ddddocr.DdddOcr(show_ad=False)

# Селекторы
URL = os.getenv("C20")
S_FIO = os.getenv("C21")      # Поле ФИО
S_REGION = os.getenv("C22")   # Выпадающий список региона
S_BTN = os.getenv("C23")      # Кнопка поиска
S_DROPDOWN = os.getenv("C24") # Опция dropdown
S_MODAL = os.getenv("C25")    # Модалка капчи
S_IMG = os.getenv("C26")      # Изображение капчи
S_INPUT = os.getenv("C27")    # Поле ввода кода
S_SUBMIT = os.getenv("C28")   # Кнопка Отправить
S_REFRESH = os.getenv("C29")  # Кнопка Обновить
MAX_T = int(os.getenv("C30", "10"))

# Данные
D_FIO = os.getenv("D21")
D_REGION = os.getenv("D22")

def process_challenge(page):
    print("\n[DEBUG] Ищу окно верификации...")
    try:
        # 1. Ждем модалку
        page.wait_for_selector(S_MODAL, state="visible", timeout=10000)

        # 2. Ищем картинку агрессивно
        # Сначала пробуем твой селектор, если нет - любую картинку в модалке
        img_node = page.locator(S_MODAL).locator("img").first

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
            page.locator(S_REFRESH).first.click()
            time.sleep(2)
            return False

        # 4. Ввод
        print(f"[*] Ввожу код в поле...")
        inp = page.locator(S_INPUT).filter(visible=True).first
        inp.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        inp.type(token, delay=100)

        # 5. Клик Отправить
        print("[*] Нажимаю кнопку подтверждения...")
        page.locator(S_SUBMIT).filter(has_text="Отправить").first.click()

        time.sleep(4)

        # Если модалка пропала - победа
        if not page.is_visible(S_MODAL):
            return True
        else:
            print("[-] Код не подошел. Обновляю...")
            page.locator(S_REFRESH).first.click()
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

        print(f"[*] Целевой URL: {URL}")
        page.goto(URL, wait_until="networkidle")

        # 1. ФИО
        print("[*] Ввод первичных данных...")
        print(S_FIO, D_FIO)
        page.locator(S_FIO).first.type(D_FIO, delay=60)

        # 2. Регион
        print("[*] Настройка параметров...")
        lst = page.locator(S_REGION).first
        lst.click()
        lst.type(D_REGION, delay=100)

        try:
            page.wait_for_selector(S_DROPDOWN, timeout=5000)
            page.locator(S_DROPDOWN).first.click()
        except:
            page.keyboard.press("Enter")

        time.sleep(1)

        # 3. Триггер поиска
        print("[*] Запуск процесса...")
        page.locator(S_BTN).filter(has_text="Найти").first.click()

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