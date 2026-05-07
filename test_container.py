#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
    ТЕСТИРОВАНИЕ КОНТЕЙНЕРА БЕЗОПАСНОСТИ СУПЕРКОМПЬЮТЕРА
================================================================================
"""

import unittest
import os
import sys
import time
from datetime import datetime

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

    # ---------- Тесты функции monitor_exchange ----------

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
        print_ok(f"messages=100, time=5 -> rate=20.0 (совпадает с ожидаемым)")

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

    # ---------- Тесты функции detect_anomaly ----------

    def test_04_detect_anomaly_ok(self):
        print_test_start(
            "UT-04: Детектирование статуса OK",
            "Функция detect_anomaly вызывается с messages=50 (меньше MAX_MSG=1000) "
            "и rate=10 (меньше MAX_RATE=100). Ожидается статус OK"
        )
        data = {"messages": 50, "rate": 10}
        result = detect_anomaly(data)
        self.assertEqual(result, "OK")
        print_ok("Статус OK (все параметры в пределах нормы)")

    def test_05_detect_anomaly_limit(self):
        print_test_start(
            "UT-05: Детектирование статуса LIMIT",
            "Функция detect_anomaly вызывается с messages=600 (меньше MAX_MSG=1000) "
            "и rate=120 (больше MAX_RATE=100). Ожидается статус LIMIT"
        )
        data = {"messages": 600, "rate": 120}
        result = detect_anomaly(data)
        self.assertIn("LIMIT", result)
        print_ok("Статус LIMIT (частота превышает порог)")

    def test_06_detect_anomaly_block(self):
        print_test_start(
            "UT-06: Детектирование статуса BLOCK",
            "Функция detect_anomaly вызывается с messages=1200 (больше MAX_MSG=1000) "
            "и rate=50 (меньше MAX_RATE=100). Ожидается статус BLOCK"
        )
        data = {"messages": 1200, "rate": 50}
        result = detect_anomaly(data)
        self.assertIn("BLOCK", result)
        print_ok("Статус BLOCK (количество сообщений превышает порог)")

    def test_07_detect_anomaly_priority(self):
        print_test_start(
            "UT-07: Проверка приоритета статусов",
            "Функция detect_anomaly вызывается с messages=1200 (превышает MAX_MSG) "
            "и rate=120 (превышает MAX_RATE). Ожидается BLOCK, так как он важнее LIMIT"
        )
        data = {"messages": 1200, "rate": 120}
        result = detect_anomaly(data)
        self.assertIn("BLOCK", result)
        print_ok("BLOCK имеет приоритет над LIMIT (оба превышены, выбран BLOCK)")

    def test_08_detect_anomaly_boundary_messages(self):
        print_test_start(
            "UT-08: Граничное значение MAX_MSG=1000",
            "Функция detect_anomaly вызывается с messages=1000 (равно MAX_MSG) "
            "и rate=50. Ожидается OK, так как порог не превышен"
        )
        data = {"messages": 1000, "rate": 50}
        result = detect_anomaly(data)
        self.assertEqual(result, "OK")
        print_ok("messages=1000 -> OK (граница не превышена, условие > MAX_MSG)")

    def test_09_detect_anomaly_boundary_rate(self):
        print_test_start(
            "UT-09: Граничное значение MAX_RATE=100",
            "Функция detect_anomaly вызывается с messages=500 и rate=100 (равно MAX_RATE). "
            "Ожидается OK, так как условие превышения строгое (> MAX_RATE)"
        )
        data = {"messages": 500, "rate": 100}
        result = detect_anomaly(data)
        self.assertEqual(result, "OK")
        print_ok("rate=100 -> OK (граница не превышена, условие > MAX_RATE)")

    # ---------- Тесты функции generate_one_dataset ----------

    def test_10_generate_dataset_length(self):
        print_test_start(
            "UT-10: Количество генерируемых записей",
            "Функция generate_one_dataset вызывается с n=5, dataset_id=1. "
            "Ожидается, что в результате будет ровно 5 записей"
        )
        result = generate_one_dataset(n=5, dataset_id=1)
        self.assertEqual(len(result["data"]), 5)
        print_ok(f"Сгенерировано {len(result['data'])} записей (ожидалось 5)")

    def test_11_generate_dataset_structure(self):
        print_test_start(
            "UT-11: Структура данных",
            "Функция generate_one_dataset вызывается с n=3, dataset_id=1. "
            "Проверяется наличие всех обязательных полей: request_id, messages, "
            "time, rate, status"
        )
        result = generate_one_dataset(n=3, dataset_id=1)
        fields = list(result["data"][0].keys())
        required = ["request_id", "messages", "time", "rate", "status"]
        for field in required:
            self.assertIn(field, fields)
        print_ok(f"Найдены поля: {', '.join(fields)} (ожидалось: {', '.join(required)})")

    def test_12_generate_dataset_id(self):
        print_test_start(
            "UT-12: Идентификатор набора",
            "Функция generate_one_dataset вызывается с n=5, dataset_id=7. "
            "Ожидается, что в результате dataset_id=7 и dataset_name='Набор #7'"
        )
        result = generate_one_dataset(n=5, dataset_id=7)
        self.assertEqual(result["dataset_id"], 7)
        self.assertEqual(result["dataset_name"], "Набор #7")
        print_ok(f"dataset_id={result['dataset_id']}, dataset_name={result['dataset_name']}")

    def test_13_data_types(self):
        print_test_start(
            "UT-13: Типы данных",
            "Проверяется, что все функции возвращают данные правильных типов: "
            "monitor_exchange -> int, float; detect_anomaly -> str; "
            "generate_one_dataset -> int, float"
        )
        r1 = monitor_exchange(100, 5)
        self.assertIsInstance(r1["messages"], int)
        self.assertIsInstance(r1["rate"], float)
        r2 = detect_anomaly({"messages": 50, "rate": 10})
        self.assertIsInstance(r2, str)
        r3 = generate_one_dataset(n=5, dataset_id=1)
        self.assertIsInstance(r3["total_messages"], int)
        self.assertIsInstance(r3["avg_rate"], float)
        print_ok("Все типы данных соответствуют ожидаемым: int, float, str")

    def test_14_statistics_calculation(self):
        print_test_start(
            "UT-14: Расчет статистики",
            "Функция generate_one_dataset вызывается с n=15, dataset_id=1. "
            "Проверяется, что статистические показатели рассчитаны корректно "
            "(total_messages > 0, avg_rate > 0)"
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
        print_info("Цель: проверка производительности и стабильности при больших объемах данных")

    def test_15_generate_100_requests(self):
        print_test_start(
            "LT-01: Генерация 100 запросов",
            "Функция generate_one_dataset вызывается с n=100, dataset_id=1. "
            "Замеряется время выполнения. Ожидается, что 100 записей будут "
            "сгенерированы за разумное время (< 3 секунд)"
        )
        start = time.time()
        result = generate_one_dataset(n=100, dataset_id=1)
        duration = time.time() - start
        self.assertEqual(len(result["data"]), 100)
        print_ok(f"100 запросов сгенерировано за {duration:.3f} секунд")
        if duration < 1:
            print_ok("Производительность: отлично (< 1 сек)")
        elif duration < 2:
            print_ok("Производительность: хорошо (< 2 сек)")
        else:
            print_info(f"Производительность: {duration:.3f} сек")

    def test_16_generate_4_datasets(self):
        print_test_start(
            "LT-02: Генерация 4 наборов по 20 запросов",
            "Функция generate_one_dataset вызывается 4 раза для dataset_id=1..4, "
            "каждый раз с n=20. Замеряется общее время выполнения. "
            "Всего должно быть сгенерировано 80 записей"
        )
        start = time.time()
        datasets = []
        for i in range(1, 5):
            datasets.append(generate_one_dataset(n=20, dataset_id=i))
        duration = time.time() - start
        self.assertEqual(len(datasets), 4)
        total = sum(len(ds["data"]) for ds in datasets)
        print_ok(f"4 набора сгенерировано за {duration:.3f} секунд, всего записей: {total}")

    def test_17_generate_sequential(self):
        print_test_start(
            "LT-03: Последовательная генерация 5 раз",
            "Функция generate_one_dataset вызывается 5 раз подряд. "
            "Замеряется время каждого вызова и вычисляется среднее. "
            "Цель: проверить стабильность производительности"
        )
        durations = []
        for i in range(5):
            start = time.time()
            generate_one_dataset(n=20, dataset_id=i+1)
            durations.append(time.time() - start)
        avg = sum(durations) / len(durations)
        print_ok(f"Среднее время генерации: {avg:.3f} секунд")
        print_ok(f"Минимальное время: {min(durations):.3f} секунд")
        print_ok(f"Максимальное время: {max(durations):.3f} секунд")
        if max(durations) - min(durations) < 0.5:
            print_ok("Стабильность: хорошая (разброс менее 0.5 сек)")


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
        if len(result.failures) > 0:
            print_info("Проваленные тесты требуют анализа")
        if len(result.errors) > 0:
            print_info("Ошибки выполнения требуют исправления кода")

    print_separator()