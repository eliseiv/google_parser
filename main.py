import argparse
from seleniumbase import SB
import time
import csv
import os


def scroll_to_target(sb, target_count):
    table_xpath = '//*[@id="QA0Szd"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]'
    table_element = sb.find_element(table_xpath)

    target_index = 3 + (target_count - 1) * 2
    target_xpath = f'{table_xpath}/div[{target_index}]'

    print(f"Прокручиваем до {target_count} таблиц (до div[{target_index}])")

    last_height = 0
    attempts_without_progress = 0
    max_attempts_without_progress = 5

    while True:
        scroll_height = sb.execute_script(
            "return arguments[0].scrollHeight", table_element)
        current_position = sb.execute_script(
            "return arguments[0].scrollTop", table_element)

        print(f"Позиция: {current_position}/{scroll_height}")

        try:
            sb.wait_for_element_present(target_xpath, timeout=5)
            print(f"Найден div[{target_index}], прокрутка завершена")
            break

        except Exception:
            sb.execute_script("arguments[0].scrollTop += 2000", table_element)
            time.sleep(5)

            new_height = sb.execute_script(
                "return arguments[0].scrollHeight", table_element)
            if new_height == last_height:
                attempts_without_progress += 1
                if attempts_without_progress >= max_attempts_without_progress:
                    print("Достигнут конец списка, больше нет данных для подгрузки")
                    break
            else:
                attempts_without_progress = 0
            last_height = new_height

    visible_tables = 0
    i = 3
    while True:
        if sb.is_element_present(f'{table_xpath}/div[{i}]'):
            visible_tables += 1
            i += 2
        else:
            break

    print(f"Прокрутка завершена, видимых таблиц: {visible_tables}")
    return visible_tables


def collect_data(sb, count, url):
    table_xpath = '//*[@id="QA0Szd"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]'
    results = []
    table_index = 3

    print(f"Собираем данные для {count} таблиц")

    for _ in range(count):
        name_xpath = f'{table_xpath}/div[{table_index}]/div/div[2]/div[4]/div[1]/div/div/div[2]/div[1]/div[2]'
        address_xpath = f'{table_xpath}/div[{table_index}]/div/div[2]/div[4]/div[1]/div/div/div[2]/div[4]/div[1]/span[3]/span[2]'
        link_xpath = f'{table_xpath}/div[{table_index}]/div/a'

        try:
            table_element = sb.find_element(
                f'{table_xpath}/div[{table_index}]')
            sb.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", table_element)
            time.sleep(2)

            sb.wait_for_element_present(name_xpath, timeout=10)
            sb.wait_for_element_present(link_xpath, timeout=10)

            print(f"Обрабатываем таблицу div[{table_index}]")

            name = sb.get_text(name_xpath)
            link = sb.get_attribute(link_xpath, 'href')

            try:
                sb.wait_for_element_present(address_xpath, timeout=5)
                address = sb.get_text(address_xpath)
            except Exception:
                address = "-"
                print(
                    f"Адрес для div[{table_index}] отсутствует, записываем '-'")

            results.append({
                'URL': url,  # Добавляем URL в данные
                'Name': name,
                'Address': address,
                'Link': link
            })

            print(f"Добавлена таблица: {name}")
            table_index += 2

        except Exception as e:
            print(f"Ошибка при сборе данных для div[{table_index}]: {str(e)}")
            try:
                alt_address_xpath = f'{table_xpath}/div[{table_index}]/div/div[2]/div[4]/div[1]/div/div/div[2]/div[4]/div[1]'
                name = sb.get_text(name_xpath)
                link = sb.get_attribute(link_xpath, 'href')
                try:
                    address = sb.get_text(alt_address_xpath)
                except:
                    address = "-"
                    print(
                        f"Альтернативный адрес для div[{table_index}] отсутствует, записываем '-'")

                results.append({
                    'URL': url,  # Добавляем URL в данные
                    'Name': name,
                    'Address': address,
                    'Link': link
                })
                print(f"Добавлена таблица с альтернативным адресом: {name}")
                table_index += 2
            except Exception as alt_e:
                print(f"Альтернативный сбор тоже провалился: {str(alt_e)}")
                break

    return results


def write_to_csv(results, append=False):
    mode = 'a' if append else 'w'
    file_exists = os.path.exists('restaurants.csv')
    with open('restaurants.csv', mode, newline='', encoding='utf-8') as csvfile:
        fieldnames = ['URL', 'Name', 'Address',
                      'Link']  # Обновляем список колонок
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists and not append:
            writer.writeheader()
        for result in results:
            writer.writerow(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Collect restaurant data')
    parser.add_argument('-c', '--count', type=int, required=True,
                        help='Number of tables to collect per URL')
    args = parser.parse_args()

    with open('links.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    with SB(uc=True, browser='chrome') as sb:
        all_results = []
        for url_index, url in enumerate(urls, 1):
            print(f"\nОбработка URL #{url_index}: {url}")
            sb.open(url)
            print("Страница открыта, ждем загрузки")
            time.sleep(15)

            visible_count = scroll_to_target(sb, args.count)
            actual_count = min(visible_count, args.count)
            # Передаем URL в collect_data
            results = collect_data(sb, actual_count, url)
            all_results.extend(results)

            write_to_csv(results, append=(url_index > 1))

            print(
                f"Завершена обработка URL #{url_index}, собрано {len(results)} из {args.count} таблиц")
            if visible_count < args.count:
                print(
                    f"Внимание: в списке было меньше таблиц ({visible_count}), чем запрошено ({args.count})")

        print(
            f"\nОбработка всех URL завершена, всего собрано {len(all_results)} таблиц")
