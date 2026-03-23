import re
import json

def parse_codegen(code_text):
    lines = code_text.strip().split('\n')
    
    # 1. Достаем URL
    url = ""
    for line in lines:
        url_match = re.search(r'page\.goto\("([^"]+)"\)', line)
        if url_match:
            url = url_match.group(1)
            break

    actions_raw = []
    
    # 2. Вытаскиваем все действия по порядку
    for line in lines:
        line = line.strip()
        
        # Ввод текста
        m_fill = re.search(r'page\.(get_by_\w+|locator)\("?([^",)]+)"?(?:,\s*name="?([^")]*)"?)?\)\.(fill|type)\("([^"]+)"\)', line)
        if m_fill:
            method, arg, name, act, val = m_fill.groups()
            sel = f"{method.replace('get_by_', '')}:{arg}" + (f"[name='{name}']" if name else "")
            actions_raw.append({"type": "force_fill", "selector": sel, "raw": line})
            continue

        # Клики
        m_click = re.search(r'page\.(get_by_\w+|locator)\("?([^",)]+)"?(?:,\s*name="?([^")]*)"?)?\)\.click\(\)', line)
        if m_click:
            method, arg, name = m_click.groups()
            sel = f"{method.replace('get_by_', '')}:{arg}" + (f"[name='{name}']" if name else "")
            actions_raw.append({"type": "click", "selector": sel, "raw": line})

    # 3. Интерактивная разметка (Отделяем форму от капчи)
    print("\n=== НАЙДЕННЫЕ ШАГИ ===")
    for i, act in enumerate(actions_raw):
        print(f"[{i}] {act['type'].upper()} -> {act['selector']}")

    print("\n--- РАЗДЕЛЕНИЕ ---")
    split_idx = int(input("Введите НОМЕР шага, на котором нажата главная кнопка (например 'Найти'): "))
    img_idx = input("Номер шага КЛИК ПО КАРТИНКЕ КАПЧИ (если есть, иначе Enter): ")
    inp_idx = input("Номер шага ВВОД В КАПЧУ: ")
    sub_idx = input("Номер шага КЛИК ОТПРАВИТЬ КАПЧУ: ")

    # 4. Формируем финальный JSON
    final_actions = []
    arg_count = 0

    for i in range(split_idx + 1):
        act = actions_raw[i]
        step = {"type": act["type"], "selector": act["selector"]}
        if act["type"] == "force_fill":
            step["arg_index"] = arg_count
            arg_count += 1
        final_actions.append(step)

    captcha = {
        "modal": "",
        "image": actions_raw[int(img_idx)]["selector"] if img_idx.isdigit() else "IMG_SELECTOR_HERE",
        "input": actions_raw[int(inp_idx)]["selector"] if inp_idx.isdigit() else "INPUT_SELECTOR_HERE",
        "submit": actions_raw[int(sub_idx)]["selector"] if sub_idx.isdigit() else "SUBMIT_SELECTOR_HERE",
        "refresh": actions_raw[int(img_idx)]["selector"] if img_idx.isdigit() else "REFRESH_SELECTOR_HERE",
        "max_tries": 10
    }

    result = {
        "new_generated_site": {
            "url": url,
            "actions": final_actions,
            "captcha": captcha
        }
    }

    print("\n\n=== ВОТ ТВОЯ 'ДЕВСТВЕННАЯ ПЛАСТИНКА' (Копируй в scenarios.json) ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n[!] Сценарий ожидает {arg_count} аргументов после флага -d.")
    print("[!] Не забудь проверить селекторы капчи и поправить тип 'dropdown' вручную, если это хитрый список (как на ФССП).")

if __name__ == "__main__":
    print("--- Вставь код из Playwright Codegen и нажми Ctrl+D (Mac/Linux) или Ctrl+Z (Windows) ---")
    lines = []
    try:
        while True: lines.append(input())
    except EOFError: pass
    parse_codegen("\n".join(lines))