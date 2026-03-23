import argparse
import json
import importlib
import sys

def main():
    parser = argparse.ArgumentParser(description="Universal Scraper Controller")
    parser.add_argument("-s", "--scenario", required=True, help="Имя сценария в JSON")
    parser.add_argument("-d", "--data", nargs='+', default=[], help="Данные для ввода")
    args = parser.parse_args()

    # 1. Загружаем scenarios.json
    try:
        with open("scenarios.json", "r", encoding="utf-8") as f:
            scenarios = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения scenarios.json: {e}")
        return

    if args.scenario not in scenarios:
        print(f"Сценарий '{args.scenario}' не найден!")
        return

    plan = scenarios[args.scenario]
    engine_type = plan.get('engine', 'classic')

    # 2. Динамически подключаем нужный движок
    try:
        if engine_type == "modern":
            import modern as engine
        else:
            import classic as engine
        
        # 3. Запускаем
        engine.run(plan, args.data)
        print("\n[DONE] Процесс завершен.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()