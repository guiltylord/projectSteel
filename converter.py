import re
import json

def convert_codegen_to_blueprint():
    print("--- Вставь код из Playwright Codegen и нажми Ctrl+Z (Windows) или Ctrl+D (Mac/Linux) ---")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    
    code = "\n".join(lines)
    
    # 1. Достаем URL
    url_match = re.search(r'page\.goto\("([^"]+)"\)', code)
    url = url_match.group(1) if url_match else ""
    
    actions = []
    arg_counter = 0

    # 2. Ищем все действия (в порядке их следования в коде)
    for line in lines:
        line = line.strip()
        
        # Обработка Ввода (fill/type)
        fill_match = re.search(r'page\.locator\("([^"]+)"\)\.(?:fill|type)\("([^"]+)"\)', line)
        if fill_match:
            selector = fill_match.group(1)
            actions.append({
                "type": "fill",
                "selector": selector,
                "arg_index": arg_counter
            })
            arg_counter += 1
            continue
            
        # Умные локаторы Playwright (get_by_placeholder, get_by_role)
        smart_fill = re.search(r'page\.get_by_(placeholder|role)\("([^"]+)"(?:,\s*name="([^"]+)")?\)\.(?:fill|type)\("([^"]+)"\)', line)
        if smart_fill:
            method, arg, name, _ = smart_fill.groups()
            selector = f"[{method}='{arg}']" if method == "placeholder" else f"{arg}:has-text('{name}')"
            actions.append({
                "type": "fill",
                "selector": selector,
                "arg_index": arg_counter
            })
            arg_counter += 1
            continue

        # Обработка Кликов
        click_match = re.search(r'page\.locator\("([^"]+)"\)\.click\(\)', line)
        if click_match:
            actions.append({
                "type": "click",
                "selector": click_match.group(1)
            })
            continue
            
        smart_click = re.search(r'page\.get_by_(placeholder|role)\("([^"]+)"(?:,\s*name="([^"]+)")?\)\.click\(\)', line)
        if smart_click:
            method, arg, name = smart_click.groups()
            selector = f"[{method}='{arg}']" if method == "placeholder" else f"button:has-text('{name}')"
            actions.append({
                "type": "click",
                "selector": selector
            })

    # Собираем девственный JSON
    scenario = {
        "NEW_GENERATED_SCENARIO": {
            "url": url,
            "actions": actions,
            "captcha": {
                "image": "ВСТАВЬ_СЕЛЕКТОР_КАРТИНКИ",
                "input": "ВСТАВЬ_СЕЛЕКТОР_ПОЛЯ_ВВОДА",
                "submit": "ВСТАВЬ_СЕЛЕКТОР_КНОПКИ",
                "refresh": "ВСТАВЬ_СЕЛЕКТОР_КНОПКИ_ОБНОВИТЬ",
                "max_tries": 5
            }
        }
    }

    print("\n\n=== ВОТ ТВОЯ ДЕВСТВЕННАЯ ПЛАСТИНКА (Копируй в scenarios.json) ===")
    print(json.dumps(scenario, indent=2, ensure_ascii=False))
    print(f"\nЭтот сценарий ожидает {arg_counter} аргументов на вход (-d).")

if __name__ == "__main__":
    convert_codegen_to_blueprint()