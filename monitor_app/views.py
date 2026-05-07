from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.cache import never_cache
from django.conf import settings
import os
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime
import random
import shutil

# ====================================================================
# НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ====================================================================

MAX_MSG = int(os.getenv("MAX_MSG", 1000))
MAX_RATE = int(os.getenv("MAX_RATE", 100))
API_KEY = os.getenv("API_KEY", "default")

# Папка для изображений
IMAGES_DIR = os.path.join(settings.MEDIA_ROOT, "charts")
os.makedirs(IMAGES_DIR, exist_ok=True)


# ====================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ====================================================================

def clear_all_charts():
    """Очищает папку с графиками"""
    try:
        if os.path.exists(IMAGES_DIR):
            for file in os.listdir(IMAGES_DIR):
                if file.endswith(".png"):
                    os.remove(os.path.join(IMAGES_DIR, file))
            print(f"[INFO] Очищена папка с графиками")
    except Exception as e:
        print(f"[ERROR] Ошибка очистки: {e}")


def save_plot_to_file(plt_figure, filename):
    """Сохраняет график в файл (перезаписывает если существует)"""
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        filepath = os.path.join(IMAGES_DIR, filename)
        plt_figure.savefig(filepath, dpi=80, bbox_inches="tight")
        plt.close()
        return f"{settings.MEDIA_URL}charts/{filename}"
    except Exception as e:
        print(f"Error saving plot: {e}")
        return None


def monitor_exchange(messages, time):
    """Расчет частоты обмена сообщениями"""
    rate = messages / time if time > 0 else 0
    return {"messages": messages, "time": time, "rate": round(rate, 2)}


def detect_anomaly(data):
    """Детектирование аномалий (OK, LIMIT, BLOCK)"""
    if data["messages"] > MAX_MSG:
        return "BLOCK: too many messages"
    if data["rate"] > MAX_RATE:
        return "LIMIT: high exchange rate"
    return "OK"


def generate_one_dataset(n=15, dataset_id=1):
    """Генерация одного набора случайных тестовых данных"""
    messages = np.random.randint(50, 1500, n).tolist()
    times = np.random.randint(1, 20, n).tolist()

    dataset_results = []
    for i, (m, t) in enumerate(zip(messages, times)):
        data = monitor_exchange(m, t)
        status = detect_anomaly(data)
        dataset_results.append(
            {
                "request_id": i + 1,
                "messages": int(m),
                "time": int(t),
                "rate": float(data["rate"]),
                "status": str(status),
            }
        )

    df = pd.DataFrame(dataset_results)
    dataset_stats = {
        "dataset_id": int(dataset_id),
        "dataset_name": f"Набор #{dataset_id}",
        "total_requests": int(len(dataset_results)),
        "blocked": int(
            len(
                [
                    r
                    for r in dataset_results
                    if r["status"] == "BLOCK: too many messages"
                ]
            )
        ),
        "limited": int(
            len(
                [
                    r
                    for r in dataset_results
                    if r["status"] == "LIMIT: high exchange rate"
                ]
            )
        ),
        "ok": int(len([r for r in dataset_results if r["status"] == "OK"])),
        "avg_rate": float(round(df["rate"].mean(), 2)) if len(df) > 0 else 0,
        "max_rate": float(df["rate"].max()) if len(df) > 0 else 0,
        "min_rate": float(df["rate"].min()) if len(df) > 0 else 0,
        "total_messages": int(df["messages"].sum()) if len(df) > 0 else 0,
        "avg_messages": float(round(df["messages"].mean(), 2)) if len(df) > 0 else 0,
        "data": dataset_results,
    }

    return dataset_stats


def generate_all_datasets(num_datasets=3, samples_per_dataset=15):
    """Генерация всех наборов данных через цикл"""
    all_datasets = []
    for i in range(1, num_datasets + 1):
        dataset = generate_one_dataset(n=samples_per_dataset, dataset_id=i)
        all_datasets.append(dataset)
    return all_datasets


def create_dataset_visualization(dataset):
    """Создание визуализации для отдельного набора данных"""
    if not dataset or not dataset.get("data"):
        return {}

    df = pd.DataFrame(dataset["data"])
    visualizations = {}

    try:
        # 1. Линейный график rate
        fig = plt.figure(figsize=(10, 6))
        plt.plot(
            df.index, df["rate"], marker="o", linewidth=2, markersize=6, color="blue"
        )
        plt.title(
            f"{dataset['dataset_name']} - Частота обмена",
            fontsize=12,
            fontweight="bold",
        )
        plt.xlabel("Запрос", fontsize=10)
        plt.ylabel("Частота (сообщ/сек)", fontsize=10)
        plt.axhline(y=MAX_RATE, color="red", linestyle="--", label=f"Порог: {MAX_RATE}")
        plt.legend(fontsize=9)
        plt.grid(True, alpha=0.3)
        url = save_plot_to_file(fig, f"ds{dataset['dataset_id']}_rate.png")
        if url:
            visualizations["rate_line"] = url

        # 2. Столбчатая диаграмма сообщений
        fig = plt.figure(figsize=(10, 6))
        colors = ["red" if m > MAX_MSG else "steelblue" for m in df["messages"]]
        plt.bar(df.index, df["messages"], color=colors, alpha=0.8)
        plt.title(
            f"{dataset['dataset_name']} - Количество сообщений",
            fontsize=12,
            fontweight="bold",
        )
        plt.xlabel("Запрос", fontsize=10)
        plt.ylabel("Сообщений", fontsize=10)
        plt.axhline(y=MAX_MSG, color="red", linestyle="--", label=f"Порог: {MAX_MSG}")
        plt.legend(fontsize=9)
        plt.grid(True, alpha=0.3, axis="y")
        url = save_plot_to_file(fig, f"ds{dataset['dataset_id']}_messages.png")
        if url:
            visualizations["messages_bar"] = url

        # 3. Круговая диаграмма статусов
        fig = plt.figure(figsize=(7, 7))
        status_counts = df["status"].value_counts()
        colors_pie = {
            "OK": "#2ecc71",
            "LIMIT: high exchange rate": "#f39c12",
            "BLOCK: too many messages": "#e74c3c",
        }
        pie_colors = [
            colors_pie.get(status, "#95a5a6") for status in status_counts.index
        ]
        plt.pie(
            status_counts.values,
            labels=status_counts.index,
            autopct="%1.1f%%",
            colors=pie_colors,
            startangle=90,
            textprops={"fontsize": 9},
        )
        plt.title(
            f"{dataset['dataset_name']} - Статусы", fontsize=12, fontweight="bold"
        )
        url = save_plot_to_file(fig, f"ds{dataset['dataset_id']}_pie.png")
        if url:
            visualizations["status_pie"] = url

    except Exception as e:
        print(f"Visualization error: {e}")

    return visualizations


def create_comparison_visualization(all_datasets):
    """Создание сравнительных графиков для всех наборов данных"""
    visualizations = {}

    if not all_datasets or len(all_datasets) == 0:
        return visualizations

    try:
        dataset_names = [d.get("dataset_name", "Unknown") for d in all_datasets]

        # 1. Сравнение частоты обмена
        fig = plt.figure(figsize=(12, 6))
        colors = ["blue", "red", "green", "orange", "purple"]

        for idx, dataset in enumerate(all_datasets):
            if dataset.get("data"):
                df = pd.DataFrame(dataset["data"])
                plt.plot(
                    df.index,
                    df["rate"],
                    marker="o",
                    linewidth=1.5,
                    markersize=3,
                    color=colors[idx % len(colors)],
                    label=dataset["dataset_name"],
                    alpha=0.7,
                )

        plt.title("Сравнение частоты обмена", fontsize=12, fontweight="bold")
        plt.xlabel("Запрос", fontsize=10)
        plt.ylabel("Частота (сообщ/сек)", fontsize=10)
        plt.axhline(
            y=MAX_RATE,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Порог: {MAX_RATE}",
        )
        plt.legend(loc="best", fontsize=8)
        plt.grid(True, alpha=0.3)
        url = save_plot_to_file(fig, "compare_line.png")
        if url:
            visualizations["comparison_line"] = url

        # 2. Всего сообщений vs Заблокированные сообщения
        fig, ax = plt.subplots(figsize=(12, 6))

        blocked_messages_counts = []
        for dataset in all_datasets:
            blocked_msgs = 0
            if dataset.get("data"):
                for row in dataset["data"]:
                    if row["status"] == "BLOCK: too many messages":
                        blocked_msgs += row["messages"]
            blocked_messages_counts.append(blocked_msgs)

        total_messages = [d.get("total_messages", 0) for d in all_datasets]

        x = np.arange(len(all_datasets))
        width = 0.35

        ax.bar(
            x - width / 2,
            total_messages,
            width,
            label="Всего сообщений",
            color="steelblue",
            alpha=0.8,
            edgecolor="black",
            linewidth=0.5,
        )
        ax.bar(
            x + width / 2,
            blocked_messages_counts,
            width,
            label="Заблокированные сообщения",
            color="#e74c3c",
            alpha=0.8,
            edgecolor="black",
            linewidth=0.5,
        )

        ax.set_xlabel("Наборы данных", fontsize=11)
        ax.set_ylabel("Количество сообщений", fontsize=11)
        ax.set_title(
            "Сообщения: всего vs заблокированные", fontsize=12, fontweight="bold"
        )
        ax.set_xticks(x)
        ax.set_xticklabels(dataset_names, rotation=15, ha="right", fontsize=9)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3, axis="y")

        url = save_plot_to_file(fig, "compare_messages.png")
        if url:
            visualizations["messages_vs_blocked"] = url

        # 3. Процент заблокированных сообщений
        fig, ax = plt.subplots(figsize=(10, 5))

        blocked_percentages = []
        for i, dataset in enumerate(all_datasets):
            total = total_messages[i]
            blocked = blocked_messages_counts[i]
            pct = (blocked / total * 100) if total > 0 else 0
            blocked_percentages.append(pct)

        bars = ax.bar(
            dataset_names,
            blocked_percentages,
            color="#e74c3c",
            alpha=0.8,
            edgecolor="black",
            linewidth=0.5,
        )

        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_xlabel("Наборы данных", fontsize=11)
        ax.set_ylabel("Процент (%)", fontsize=11)
        ax.set_title("Доля заблокированных сообщений", fontsize=12, fontweight="bold")
        ax.set_ylim(0, 100)
        plt.xticks(rotation=15, ha="right", fontsize=9)
        ax.grid(True, alpha=0.3, axis="y")

        url = save_plot_to_file(fig, "compare_percentage.png")
        if url:
            visualizations["blocked_percentage"] = url

        # 4. Сравнение средней частоты
        fig = plt.figure(figsize=(10, 5))
        avg_rates = [float(d.get("avg_rate", 0)) for d in all_datasets]
        colors_bar = ["#2ecc71" if rate < MAX_RATE else "#e74c3c" for rate in avg_rates]

        bars = plt.barh(
            dataset_names,
            avg_rates,
            color=colors_bar,
            alpha=0.8,
            edgecolor="black",
            linewidth=0.5,
        )

        for bar in bars:
            width_val = bar.get_width()
            if width_val > 0:
                plt.annotate(
                    f"{width_val:.1f}",
                    xy=(width_val, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0),
                    textcoords="offset points",
                    ha="left",
                    va="center",
                    fontsize=9,
                )

        plt.axvline(
            x=MAX_RATE,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Порог: {MAX_RATE}",
        )
        plt.xlabel("Средняя частота", fontsize=11)
        plt.title("Средняя частота обмена", fontsize=12, fontweight="bold")
        plt.legend(fontsize=9)
        plt.grid(True, alpha=0.3, axis="x")

        url = save_plot_to_file(fig, "compare_avgrate.png")
        if url:
            visualizations["comparison_horizontal"] = url

    except Exception as e:
        print(f"Comparison visualization error: {e}")

    return visualizations


# ====================================================================
# ФУНКЦИИ ПРЕДСТАВЛЕНИЙ (VIEWS) С CSRF-ЗАЩИТОЙ
# ====================================================================

def index(request):
    """Перенаправление на страницу входа"""
    return redirect("login")


@never_cache
@csrf_protect
def login_view(request):
    """
    Страница аутентификации с CSRF-защитой
    При POST-запросе проверяет API_KEY
    """
    if request.method == "POST":
        api_key = request.POST.get("api_key", "")
        if api_key == API_KEY:
            request.session["authenticated"] = True
            messages.success(request, "Доступ разрешен!")
            return redirect("monitor")
        else:
            messages.error(request, "Неверный ключ доступа!")
    return render(request, "login.html")


def logout_view(request):
    """Выход из системы - очистка сессии"""
    request.session.flush()
    messages.info(request, "Вы вышли из системы")
    return redirect("login")


@never_cache
@csrf_protect
def monitor(request):
    """
    Главная страница мониторинга
    Требует аутентификации, иначе редирект на login
    """
    if not request.session.get("authenticated", False):
        return redirect("login")

    return render(
        request,
        "monitor.html",
        {
            "max_msg": MAX_MSG,
            "max_rate": MAX_RATE,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@csrf_exempt
def api_get_datasets(request):
    """
    API endpoint для получения данных
    Возвращает JSON с наборами данных и визуализациями
    """
    if request.method == "GET":
        try:
            # Очищаем папку перед генерацией новых графиков
            clear_all_charts()

            num_datasets = int(request.GET.get("num_datasets", 3))
            samples_per_dataset = int(request.GET.get("samples", 15))

            # Ограничиваем размер данных
            if samples_per_dataset > 30:
                samples_per_dataset = 30
            if num_datasets > 4:
                num_datasets = 4

            # Генерируем все наборы данных через цикл
            all_datasets = generate_all_datasets(num_datasets, samples_per_dataset)

            result_datasets = []
            for dataset in all_datasets:
                # Создаем визуализации для каждого набора
                viz = create_dataset_visualization(dataset)

                # Создаем HTML таблицу ПОЛНОСТЬЮ
                table_rows = ""
                for i, row in enumerate(dataset["data"]):
                    status_class = (
                        "status-ok"
                        if row["status"] == "OK"
                        else (
                            "status-limit"
                            if "LIMIT" in row["status"]
                            else "status-block"
                        )
                    )
                    table_rows += f"<tr>"
                    table_rows += f"<td>{i + 1}</td>"
                    table_rows += f"<td>{row['messages']}</td>"
                    table_rows += f"<td>{row['time']}</td>"
                    table_rows += f"<td>{row['rate']}</td>"
                    table_rows += f'<td class="{status_class}">{row["status"]}</td>'
                    table_rows += f"</tr>"

                cleaned_dataset = {
                    "dataset_id": int(dataset["dataset_id"]),
                    "dataset_name": str(dataset["dataset_name"]),
                    "total_requests": int(dataset["total_requests"]),
                    "blocked": int(dataset["blocked"]),
                    "limited": int(dataset["limited"]),
                    "ok": int(dataset["ok"]),
                    "avg_rate": float(dataset["avg_rate"]),
                    "max_rate": float(dataset["max_rate"]),
                    "min_rate": float(dataset["min_rate"]),
                    "total_messages": int(dataset["total_messages"]),
                    "avg_messages": float(dataset["avg_messages"]),
                    "viz": viz,
                    "table_rows": table_rows,
                }
                result_datasets.append(cleaned_dataset)

            # Создаем общие сравнительные графики
            comparison_viz = create_comparison_visualization(all_datasets)

            # Общая статистика
            total_stats = {
                "total_datasets": int(len(all_datasets)),
                "total_requests": int(
                    sum(d.get("total_requests", 0) for d in all_datasets)
                ),
                "total_ok": int(sum(d.get("ok", 0) for d in all_datasets)),
                "total_limited": int(sum(d.get("limited", 0) for d in all_datasets)),
                "total_blocked": int(sum(d.get("blocked", 0) for d in all_datasets)),
                "total_avg_rate": float(
                    round(
                        sum(d.get("avg_rate", 0) for d in all_datasets)
                        / len(all_datasets),
                        2,
                    )
                )
                if all_datasets
                else 0,
            }

            response = {
                "datasets": result_datasets,
                "comparison_viz": comparison_viz,
                "total_stats": total_stats,
                "success": True,
            }

            return JsonResponse(response)

        except Exception as e:
            print(f"Error in api_get_datasets: {e}")
            import traceback

            traceback.print_exc()
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid method"}, status=400)