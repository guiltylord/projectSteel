from playwright.sync_api import sync_playwright
import json

scenario = {
    "url": "",
    "actions": [],
    "captcha": {"popup": "", "image": "", "input": "", "submit": ""}
}

# Скрипт генерации селекторов (внедряется в браузер)
JS_HELPER = """
    (() => {
        window.lastElement = null;
        
        // Отслеживаем движение мыши и запоминаем элемент
        document.addEventListener('mouseover', (e) => {
            if (window.lastElement) {
                window.lastElement.style.outline = '';
            }
            e.target.style.outline = '3px solid red';
            window.lastElement = e.target;
        });

        // Функция генерации селектора
        window.getBestSelector = () => {
            const el = window.lastElement;
            if (!el) return null;

            // 1. Приоритет: ID
            if (el.id && !el.id.match(/\d{5,}/) && el.id.length < 30) return '#' + el.id;
            
            // 2. Приоритет: Name
            if (el.name) return `[name="${el.name}"]`;
            
            // 3. Приоритет: Placeholder
            if (el.placeholder) return `[placeholder="${el.placeholder}"]`;
            
            // 4. Картинка с ID (часто для капчи)
            if (el.tagName === 'IMG' && el.id) return '#' + el.id;

            // 5. Кнопка с типом submit
            if (el.type === 'submit') return 'input[type="submit"]';
            
            // 6. Текст (для кнопок типа <span>Найти</span>)
            if ((el.tagName === 'BUTTON' || el.tagName === 'SPAN' || el.tagName === 'A') && el.innerText.trim().length > 0 && el.innerText.trim().length < 20) {
                 return `text=${el.innerText.trim()}`;
            }

            // 7. Классы (фильтруем мусорные классы фреймворков)
            if (el.className && typeof el.className === 'string') {
                const validClasses = el.className.split(' ')
                    .filter(c => !c.startsWith('css-') && !c.startsWith('vs__') && c.length > 2);
                if (validClasses.length > 0) return '.' + validClasses.join('.');
            }

            return el.tagName.toLowerCase();
        }
        
        window.getTagName = () => window.lastElement ? window.lastElement.tagName : 'NULL';
    })()
"""

def run_inspector():
    url = input("URL (Enter для дефолтного): ")
    if not url: 
        return "Прервано. Не введен URL"
    scenario['url'] = url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        
        # Включаем подсветку
        page.evaluate(JS_HELPER)

        print("\n" + "="*60)
        print(" РЕЖИМ БЕСКОНТАКТНОГО СБОРА ")
        print("="*60)
        print("1. Наведи мышку на элемент в браузере (он станет красным).")
        print("2. Не убирая мышку (или оставив её там), перейди в это окно.")
        print("3. Введи команду:")
        print("   f  -> Поле ввода (Fill)")
        print("   s  -> Выбор из списка/Дата (JS Set)")
        print("   c  -> Клик (Click)")
        print("   ---------------------------")
        print("   ci -> Картинка капчи")
        print("   cn -> Поле ввода капчи")
        print("   cs -> Кнопка отправить капчу")
        print("   ---------------------------")
        print("   r  -> Обновить подсветку (если перешел на новую страницу)")
        print("   q  -> ВЫХОД и сохранение")
        print("="*60)

        while True:
            cmd = input("\n[Наведи и введи] >>> ").strip().lower()

            if cmd == 'q':
                break
            
            if cmd == 'r':
                page.evaluate(JS_HELPER)
                print("Скрипт подсветки перезагружен (нужно после смены страницы).")
                continue

            # Получаем данные от браузера
            try:
                selector = page.evaluate("window.getBestSelector()")
                tag = page.evaluate("window.getTagName()")
                
                if not selector:
                    print("!!! Элемент не выбран (наведи мышку на что-нибудь)")
                    continue

                print(f"   Пойман элемент: <{tag}> {selector}")

                if cmd == 'f':
                    var_name = input("   Имя переменной для .env (например D1): ").upper()
                    scenario['actions'].append({
                        "type": "fill", 
                        "selector": selector, 
                        "value": "os.getenv('" + var_name + "')"
                    })
                    print(f"   [+] Добавлено: Заполнить {selector}")

                elif cmd == 's':
                    var_name = input("   Имя переменной для .env (например D5): ").upper()
                    scenario['actions'].append({
                        "type": "js_fill", 
                        "selector": selector, 
                        "value": "os.getenv('" + var_name + "')"
                    })
                    print(f"   [+] Добавлено: JS-заполнение {selector}")

                elif cmd == 'c':
                    scenario['actions'].append({
                        "type": "click", 
                        "selector": selector
                    })
                    print(f"   [+] Добавлено: Клик по {selector}")
                    print("   (Теперь нажми эту кнопку в браузере САМ, чтобы перейти дальше)")

                elif cmd == 'ci':
                    scenario['captcha']['image'] = selector
                    print("   [v] Записано как картинка капчи")
                elif cmd == 'cn':
                    scenario['captcha']['input'] = selector
                    print("   [v] Записано как ввод капчи")
                elif cmd == 'cs':
                    scenario['captcha']['submit'] = selector
                    print("   [v] Записано как кнопка капчи")

            except Exception as e:
                print(f"Ошибка связи с браузером: {e}")

        browser.close()

    print("\n\n=== ТВОЙ СЦЕНАРИЙ JSON ===")
    print(json.dumps(scenario, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_inspector()