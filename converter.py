import re
import json

def parse_selector(method, arg, name):
    """Генерирует селекторы в формате, понятном нашему resolve_locator"""
    if method == "get_by_role":
        return f"role:{arg}[name='{name}']" if name else f"role:{arg}"
    if method == "get_by_placeholder":
        return f"placeholder:{arg}"
    if method == "get_by_text":
        return f"text:{arg}"
    if method == "locator":
        return arg
    return arg

def extract_action(line):
    line = line.strip()
    
    # 1. Ввод (fill/type)
    match_fill = re.search(r'page\.(get_by_\w+|locator)\("?([^",)]+)"?(?:,\s*name="?([^")]*)"?)?\)\.(?:fill|type)\("([^"]+)"\)', line)
    if match_fill:
        method, arg, name, value = match_fill.groups()
        return {"type": "fill", "selector": parse_selector(method, arg, name), "raw": line}

    # 2. Клик (click)
    match_click = re.search(r'page\.(get_by_\w+|locator)\("?([^",)]+)"?(?:,\s*name="?([^")]*)"?)?\)\.click\(\)', line)
    if match_click:
        method, arg, name = match_click.groups()
        return {"type": "click", "selector": parse_selector(method, arg, name), "raw": line}

    # 3. Нажатие клавиши (press)
    match_press = re.search(r'page\.(get_by_\w+|locator)\("?([^",)]+)"?(?:,\s*name="?([^")]*)"?)?\)\.press\("([^"]+)"\)', line)
    if match_press:
        method, arg, name, key = match_press.groups()
        return {"type": "press", "selector": parse_selector(method, arg, name), "key": key, "raw": line}

    return None

def convert():
    print("--- Вставь код из Playwright Codegen и нажми Ctrl+Z / Ctrl+D ---")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass

    url = ""
    parsed_actions = []
    
    for line in lines:
        if 'page.goto' in line:
            url_match = re.search(r'page\.goto\("([^"]+)"\)', line)
            if url_match: url = url_match.group(1)
            continue
            
        action = extract_action(line)
        if action:
            parsed_actions.append(action)

    if not parsed_actions:
        print("Действий не найдено.")
        return

    print("\n" + "="*40)
    print(" НАЙДЕННЫЕ ЭЛЕМЕНТЫ (ВВЕДИ НОМЕР)")
    print("="*40)
    
    for i, act in enumerate(parsed_actions):
        print(f"[{i}] {act['type'].upper()} -> {act['selector']}")
        if 'key' in act: print(f"    Клавиша: {act['key']}")

    print("\n--- РАЗМЕТКА КАПЧИ ---")
    print("Если элемента нет в списке (например, кнопки обновить), просто нажми Enter.")
    
    idx_img = input("Номер шага КЛИК ПО КАРТИНКЕ КАПЧИ: ")
    idx_inp = input("Номер шага ВВОД ТЕКСТА В КАПЧУ: ")
    idx_sub = input("Номер шага КЛИК ПО КНОПКЕ 'ОТПРАВИТЬ': ")
    idx_ref = input("Номер шага КЛИК ПО КНОПКЕ 'ОБНОВИТЬ' (если есть): ")

    # Собираем селекторы капчи
    captcha_block = {}
    if idx_img.isdigit(): captcha_block["image"] = parsed_actions[int(idx_img)]["selector"]
    if idx_inp.isdigit(): captcha_block["input"] = parsed_actions[int(idx_inp)]["selector"]
    if idx_sub.isdigit(): captcha_block["submit"] = parsed_actions[int(idx_sub)]["selector"]
    if idx_ref.isdigit(): captcha_block["refresh"] = parsed_actions[int(idx_ref)]["selector"]
    captcha_block["max_tries"] = 10

    # Собираем основные шаги (всё, что не относится к капче)
    captcha_indices = [int(i) for i in [idx_img, idx_inp, idx_sub, idx_ref] if i.isdigit()]
    
    final_actions = []
    arg_counter = 0
    for i, act in enumerate(parsed_actions):
        if i in captcha_indices:
            continue # Пропускаем шаги капчи, они уже в блоке captcha_block
            
        step = {"type": act["type"], "selector": act["selector"]}
        if act["type"] == "fill":
            step["arg_index"] = arg_counter
            arg_counter += 1
        elif act["type"] == "press":
            step["key"] = act["key"]
            
        final_actions.append(step)

    scenario = {
        "NEW_GENERATED_SCENARIO": {
            "url": url,
            "actions": final_actions,
            "captcha": captcha_block
        }
    }

    print("\n=== ПУСТАЯ ПЛАСТИНКА (Копируй в scenarios.json) ===\n")
    print(json.dumps(scenario, indent=2, ensure_ascii=False))
    print(f"\nСценарий ожидает {arg_counter} аргументов на вход (-d).")

if __name__ == "__main__":
    convert()