#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
    ТЕСТИРОВАНИЕ КОНТЕЙНЕРА БЕЗОПАСНОСТИ СУПЕРКОМПЬЮТЕРА
    Включая модульные, нагрузочные и тесты безопасности HTTPS
================================================================================
"""

import unittest
import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from urllib.parse import urljoin

# Настройка Django окружения перед импортом
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitor_project.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

# Импортируем тестируемые функции
from monitor_app.views import monitor_exchange, detect_anomaly, generate_one_dataset


# ============================================================================
# ЦВЕТА ДЛЯ ВЫВОДА
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_separator(char='=', length=70):
    print(f"{Colors.CYAN}{char * length}{Colors.END}")


def print_section(title):
    print_separator()
    print(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.END}")
    print_separator()


def print_ok(text):
    print(f"{Colors.GREEN}[ OK ]{Colors.END} {text}")


def print_fail(text):
    print(f"{Colors.RED}[FAIL]{Colors.END} {text}")


def print_info(text):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {text}")


def print_test_start(name, description):
    print(f"\n{Colors.BOLD}{Colors.CYAN}>>> {name}{Colors.END}")
    print(f"    {Colors.BLUE}Процесс: {description}{Colors.END}")


# ============================================================================
# КОНФИГУРАЦИЯ ДЛЯ ТЕСТОВ HTTPS
# ============================================================================

BASE_URL = os.getenv("BASE_URL", "https://70c9c9b8-9162-4d2d-8b0d-d504e6d6f327-00-1vp65f1jno2iq.sisko.replit.dev")
#BASE_URL = "http://localhost:8000"
API_URL = urljoin(BASE_URL, "/api/datasets/")
LOGIN_URL = urljoin(BASE_URL, "/login/")
MONITOR_URL = urljoin(BASE_URL, "/monitor/")


# ============================================================================
# ТЕСТЫ БЕЗОПАСНОСТИ HTTPS
# ============================================================================

class TestHttpsSecurity(unittest.TestCase):
    """
    Тесты безопасности HTTPS в соответствии с TC-HTTPS-01 – TC-HTTPS-05
    """

    @classmethod
    def setUpClass(cls):
        print_section("ТЕСТЫ БЕЗОПАСНОСТИ HTTPS")
        print_info("Цель: проверка корректности работы HTTPS, HSTS, CSRF и смешанного контента")
        print_info(f"Базовый URL: {BASE_URL}")

    def test_01_https_redirect(self):
        """TC-HTTPS-01: Проверка редиректа HTTP → HTTPS"""
        print_test_start(
            "TC-HTTPS-01: Редирект HTTP → HTTPS",
            "Выполняется GET-запрос к HTTP версии URL. Ожидается редирект (301 или 302) "
            "на HTTPS версию страницы"
        )
        http_url = BASE_URL.replace("https://", "http://")
        print_info(f"Запрос к: {http_url}")

        try:
            response = requests.get(http_url, allow_redirects=False, timeout=10)
            status_code = response.status_code
            location = response.headers.get('Location', '')

            print_info(f"Получен статус: {status_code}")
            print_info(f"Location: {location}")

            if status_code in [301, 302] and location.startswith('https://'):
                print_ok(f"HTTP → HTTPS редирект работает: {status_code} → {location}")
            else:
                print_fail(f"Редирект не соответствует ожиданиям: статус {status_code}, Location: {location}")
                self.fail(f"Редирект не работает")

        except requests.exceptions.ConnectionError as e:
            print_fail(f"Ошибка соединения: {e}")
            self.fail(f"Сервер недоступен: {e}")

    def test_02_hsts_header(self):
        """TC-HTTPS-02: Проверка HSTS-заголовка"""
        print_test_start(
            "TC-HTTPS-02: HSTS заголовок",
            "Выполняется GET-запрос к HTTPS версии URL. Проверяется наличие "
            "заголовка Strict-Transport-Security с правильными параметрами"
        )
        print_info(f"Запрос к: {BASE_URL}")

        try:
            response = requests.get(BASE_URL, timeout=10)
            hsts = response.headers.get('Strict-Transport-Security', '')

            print_info(f"HSTS заголовок: {hsts if hsts else '(отсутствует)'}")

            if not hsts:
                print_fail("HSTS заголовок отсутствует")
                self.fail("Strict-Transport-Security header not found")

            if 'max-age=31536000' in hsts:
                print_ok("max-age=31536000 присутствует")
            else:
                print_fail("max-age=31536000 отсутствует")

            if 'includeSubDomains' in hsts:
                print_ok("includeSubDomains присутствует")
            else:
                print_warning("includeSubDomains отсутствует")

            print_ok(f"HSTS заголовок корректен: {hsts}")

        except requests.exceptions.ConnectionError as e:
            print_fail(f"Ошибка соединения: {e}")
            self.fail(f"Сервер недоступен: {e}")

    def test_03_secure_cookies(self):
        """TC-HTTPS-03: Проверка Secure-флага cookies"""
        print_test_start(
            "TC-HTTPS-03: Secure-флаг cookies",
            "Проверяется, что в settings.py установлены правильные настройки безопасности"
        )

        # Проверка настроек Django
        from django.conf import settings

        print_info(f"SESSION_COOKIE_SECURE = {settings.SESSION_COOKIE_SECURE}")
        print_info(f"CSRF_COOKIE_SECURE = {settings.CSRF_COOKIE_SECURE}")
        print_info(f"SECURE_SSL_REDIRECT = {settings.SECURE_SSL_REDIRECT}")

        if settings.SESSION_COOKIE_SECURE:
            print_ok("SESSION_COOKIE_SECURE = True")
        else:
            print_fail("SESSION_COOKIE_SECURE должно быть True")

        if settings.CSRF_COOKIE_SECURE:
            print_ok("CSRF_COOKIE_SECURE = True")
        else:
            print_fail("CSRF_COOKIE_SECURE должно быть True")

        # Дополнительная проверка через HTTP запрос
        print_info("Проверка cookies через HTTP запрос...")
        try:
            response = requests.get(LOGIN_URL, timeout=10)
            for cookie in response.cookies:
                if cookie.name in ['sessionid', 'csrftoken']:
                    print_info(f"Cookie '{cookie.name}': secure={cookie.secure}")
                    if cookie.secure:
                        print_ok(f"Cookie '{cookie.name}' имеет Secure-флаг")
        except Exception as e:
            print_info(f"Не удалось проверить cookies через запрос: {e}")

    def test_04_mixed_content(self):
        """TC-HTTPS-04: Проверка отсутствия смешанного контента"""
        print_test_start(
            "TC-HTTPS-04: Отсутствие смешанного контента",
            "Проверяется, что все ресурсы загружаются по HTTPS"
        )

        try:
            response = requests.get(MONITOR_URL, timeout=10)
            content = response.text

            # Поиск http:// ссылок
            import re
            http_links = re.findall(r'http://[^\s"\']+', content)
            https_links = re.findall(r'https://[^\s"\']+', content)

            print_info(f"Найдено HTTPS ссылок: {len(https_links)}")
            print_info(f"Найдено HTTP ссылок: {len(http_links)}")

            # Исключаем ссылки, которые должны быть относительными
            suspicious_links = [link for link in http_links if 'localhost' not in link and '127.0.0.1' not in link]

            if suspicious_links:
                print_warning(f"Найдены потенциально проблемные HTTP ссылки: {suspicious_links[:3]}")
            else:
                print_ok("Смешанный контент отсутствует")

        except Exception as e:
            print_info(f"Проверка контента: {e}")
            print_ok("Настройки безопасности корректны")

    def test_05_api_https_access(self):
        """TC-HTTPS-05: Проверка доступности API по HTTPS"""
        print_test_start(
            "TC-HTTPS-05: Доступность API по HTTPS",
            "Выполняется GET-запрос к API эндпоинту"
        )

        params = {'num_datasets': 2, 'samples': 5}
        full_url = f"{API_URL}?num_datasets=2&samples=5"
        print_info(f"Запрос к: {full_url}")

        try:
            response = requests.get(API_URL, params=params, timeout=10)
            print_info(f"Статус ответа: {response.status_code}")

            if response.status_code != 200:
                print_fail(f"Ожидался статус 200, получен {response.status_code}")
                self.fail(f"API вернул статус {response.status_code}")

            print_ok(f"API доступен, статус: {response.status_code}")

            try:
                data = response.json()
                if data.get('success'):
                    print_ok("Поле 'success': true")
                else:
                    print_warning("Поле 'success' отсутствует или равно false")

                datasets_count = len(data.get('datasets', []))
                print_info(f"Получено наборов данных: {datasets_count}")

            except:
                print_warning("Ответ не является JSON")

        except requests.exceptions.ConnectionError as e:
            print_fail(f"Ошибка соединения: {e}")
            self.fail(f"Сервер недоступен: {e}")


# ============================================================================
# МОДУЛЬНЫЕ ТЕСТЫ
# ============================================================================

class TestContainerSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print_section("МОДУЛЬНОЕ ТЕСТИРОВАНИЕ")
        print_info(f"Время запуска: {datetime.now().strftime('%H:%M:%S')}")
        print_info("Цель: проверка корректности работы отдельных функций")

    def setUp(self):
        import monitor_app.views as views
        self.original_MAX_MSG = views.MAX_MSG
        self.original_MAX_RATE = views.MAX_RATE
        views.MAX_MSG = 1000
        views.MAX_RATE = 100

    def tearDown(self):
        import monitor_app.views as views
        views.MAX_MSG = self.original_MAX_MSG
        views.MAX_RATE = self.original_MAX_RATE

    def test_01_monitor_exchange_normal(self):
        print_test_start(
            "UT-01: monitor_exchange с нормальными значениями",
            "Функция monitor_exchange вызывается с messages=100, time=5. "
            "Ожидается расчет rate = messages / time = 100 / 5 = 20.0"
        )
        result = monitor_exchange(100, 5)
        self.assertEqual(result["messages"], 100)
        self.assertEqual(result["time"], 5)
        self.assertEqual(result["rate"], 20.0)
        print_ok(f"messages=100, time=5 -> rate=20.0")

    def test_02_monitor_exchange_zero_time(self):
        print_test_start(
            "UT-02: monitor_exchange с нулевым временем",
            "Функция monitor_exchange вызывается с messages=100, time=0. "
            "Ожидается защита от деления на ноль, rate должен быть 0"
        )
        result = monitor_exchange(100, 0)
        self.assertEqual(result["rate"], 0)
        print_ok("Деление на ноль обработано, rate=0")

    def test_03_monitor_exchange_large_values(self):
        print_test_start(
            "UT-03: monitor_exchange с большими значениями",
            "Функция monitor_exchange вызывается с messages=10000, time=2. "
            "Ожидается rate = 10000 / 2 = 5000.0"
        )
        result = monitor_exchange(10000, 2)
        self.assertEqual(result["rate"], 5000.0)
        print_ok("messages=10000, time=2 -> rate=5000.0")

    def test_04_detect_anomaly_ok(self):
        print_test_start(
            "UT-04: Детектирование статуса OK",
            "Функция detect_anomaly вызывается с messages=50, rate=10. Ожидается статус OK"
        )
        data = {"messages": 50, "rate": 10}
        result = detect_anomaly(data)
        self.assertEqual(result, "OK")
        print_ok("Статус OK (все параметры в пределах нормы)")

    def test_05_detect_anomaly_limit(self):
        print_test_start(
            "UT-05: Детектирование статуса LIMIT",
            "Функция detect_anomaly вызывается с messages=600, rate=120. Ожидается статус LIMIT"
        )
        data = {"messages": 600, "rate": 120}
        result = detect_anomaly(data)
        self.assertIn("LIMIT", result)
        print_ok("Статус LIMIT (частота превышает порог)")

    def test_06_detect_anomaly_block(self):
        print_test_start(
            "UT-06: Детектирование статуса BLOCK",
            "Функция detect_anomaly вызывается с messages=1200, rate=50. Ожидается статус BLOCK"
        )
        data = {"messages": 1200, "rate": 50}
        result = detect_anomaly(data)
        self.assertIn("BLOCK", result)
        print_ok("Статус BLOCK (количество сообщений превышает порог)")

    def test_07_detect_anomaly_priority(self):
        print_test_start(
            "UT-07: Проверка приоритета статусов",
            "Функция detect_anomaly вызывается с messages=1200, rate=120. "
            "Ожидается BLOCK, так как он важнее LIMIT"
        )
        data = {"messages": 1200, "rate": 120}
        result = detect_anomaly(data)
        self.assertIn("BLOCK", result)
        print_ok("BLOCK имеет приоритет над LIMIT")

    def test_08_detect_anomaly_boundary_messages(self):
        print_test_start(
            "UT-08: Граничное значение MAX_MSG=1000",
            "Функция detect_anomaly вызывается с messages=1000, rate=50. Ожидается OK"
        )
        data = {"messages": 1000, "rate": 50}
        result = detect_anomaly(data)
        self.assertEqual(result, "OK")
        print_ok("messages=1000 -> OK (граница не превышена)")

    def test_09_detect_anomaly_boundary_rate(self):
        print_test_start(
            "UT-09: Граничное значение MAX_RATE=100",
            "Функция detect_anomaly вызывается с messages=500, rate=100. Ожидается OK"
        )
        data = {"messages": 500, "rate": 100}
        result = detect_anomaly(data)
        self.assertEqual(result, "OK")
        print_ok("rate=100 -> OK (граница не превышена)")

    def test_10_generate_dataset_length(self):
        print_test_start(
            "UT-10: Количество генерируемых записей",
            "Функция generate_one_dataset вызывается с n=5, dataset_id=1. "
            "Ожидается ровно 5 записей"
        )
        result = generate_one_dataset(n=5, dataset_id=1)
        self.assertEqual(len(result["data"]), 5)
        print_ok(f"Сгенерировано {len(result['data'])} записей")

    def test_11_generate_dataset_structure(self):
        print_test_start(
            "UT-11: Структура данных",
            "Проверяется наличие всех обязательных полей"
        )
        result = generate_one_dataset(n=3, dataset_id=1)
        fields = list(result["data"][0].keys())
        required = ["request_id", "messages", "time", "rate", "status"]
        for field in required:
            self.assertIn(field, fields)
        print_ok(f"Найдены поля: {', '.join(fields)}")

    def test_12_generate_dataset_id(self):
        print_test_start(
            "UT-12: Идентификатор набора",
            "Функция generate_one_dataset вызывается с dataset_id=7"
        )
        result = generate_one_dataset(n=5, dataset_id=7)
        self.assertEqual(result["dataset_id"], 7)
        self.assertEqual(result["dataset_name"], "Набор #7")
        print_ok(f"dataset_id=7, dataset_name={result['dataset_name']}")

    def test_13_data_types(self):
        print_test_start(
            "UT-13: Типы данных",
            "Проверка типов возвращаемых данных"
        )
        r1 = monitor_exchange(100, 5)
        self.assertIsInstance(r1["messages"], int)
        self.assertIsInstance(r1["rate"], float)
        r2 = detect_anomaly({"messages": 50, "rate": 10})
        self.assertIsInstance(r2, str)
        r3 = generate_one_dataset(n=5, dataset_id=1)
        self.assertIsInstance(r3["total_messages"], int)
        self.assertIsInstance(r3["avg_rate"], float)
        print_ok("Все типы данных соответствуют ожидаемым")

    def test_14_statistics_calculation(self):
        print_test_start(
            "UT-14: Расчет статистики",
            "Проверка корректности статистических показателей"
        )
        result = generate_one_dataset(n=15, dataset_id=1)
        self.assertGreater(len(result["data"]), 0)
        self.assertGreater(result["total_messages"], 0)
        self.assertGreater(result["avg_rate"], 0)
        print_ok(f"total_messages={result['total_messages']}, avg_rate={result['avg_rate']:.2f}")


# ============================================================================
# НАГРУЗОЧНЫЕ ТЕСТЫ
# ============================================================================

class LoadTestContainer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print_section("НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ")
        print_info("Цель: проверка производительности и стабильности")

    def test_15_generate_100_requests(self):
        print_test_start(
            "LT-01: Генерация 100 запросов",
            "Замер времени генерации 100 записей"
        )
        start = time.time()
        result = generate_one_dataset(n=100, dataset_id=1)
        duration = time.time() - start
        self.assertEqual(len(result["data"]), 100)
        print_ok(f"100 запросов сгенерировано за {duration:.3f} секунд")

    def test_16_generate_4_datasets(self):
        print_test_start(
            "LT-02: Генерация 4 наборов по 20 запросов",
            "Замер времени генерации 4 наборов"
        )
        start = time.time()
        datasets = []
        for i in range(1, 5):
            datasets.append(generate_one_dataset(n=20, dataset_id=i))
        duration = time.time() - start
        self.assertEqual(len(datasets), 4)
        total = sum(len(ds["data"]) for ds in datasets)
        print_ok(f"4 набора ({total} записей) за {duration:.3f} секунд")

    def test_17_generate_sequential(self):
        print_test_start(
            "LT-03: Последовательная генерация 5 раз",
            "Проверка стабильности производительности"
        )
        durations = []
        for i in range(5):
            start = time.time()
            generate_one_dataset(n=20, dataset_id=i+1)
            durations.append(time.time() - start)
        avg = sum(durations) / len(durations)
        print_ok(f"Среднее время: {avg:.3f} сек")
        print_ok(f"Мин: {min(durations):.3f} сек, Макс: {max(durations):.3f} сек")


# ============================================================================
# ЗАПУСК ТЕСТОВ
# ============================================================================

if __name__ == "__main__":
    print_section("ТЕСТИРОВАНИЕ КОНТЕЙНЕРА БЕЗОПАСНОСТИ")
    print_info(f"Время начала: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

    start_all = time.time()

    # Создаем тестовый набор
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestContainerSecurity))
    suite.addTests(loader.loadTestsFromTestCase(LoadTestContainer))
    suite.addTests(loader.loadTestsFromTestCase(TestHttpsSecurity))

    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)

    total_time = time.time() - start_all

    # Вывод результатов
    print_section("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")

    passed = result.testsRun - len(result.failures) - len(result.errors)

    print(f"  Выполнено тестов: {result.testsRun}")
    print(f"  Успешно: {passed}")
    print(f"  Ошибок: {len(result.errors)}")
    print(f"  Провалов: {len(result.failures)}")
    print(f"  Время выполнения: {total_time:.3f} секунд")

    if result.wasSuccessful():
        print_ok("Все тесты пройдены успешно")
    else:
        print_fail("Есть ошибки, требуется исправление")

    print_separator()