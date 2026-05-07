// Глобальные переменные
let currentDatasetId = 0;
let allDatasets = [];
let maxRate = 100;

// Функция обновления данных
async function refreshData() {
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '<div class="loading">🔄 Генерация наборов данных...</div>';

    const numDatasets = document.getElementById('num-datasets').value;
    const samplesCount = document.getElementById('samples-count').value;

    const url = `/api/datasets/?num_datasets=${numDatasets}&samples=${samplesCount}`;

    let retries = 3;
    let delay = 1000;

    while (retries > 0) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000);

            const response = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                allDatasets = data.datasets;
                currentDatasetId = 0;
                renderHTML(data);

                const now = new Date();
                document.getElementById('timestamp').innerText = now.toLocaleString('ru-RU');
                return;
            } else {
                throw new Error(data.error || 'Неизвестная ошибка');
            }
        } catch (error) {
            retries--;
            if (retries > 0) {
                console.log(`Ошибка, повторная попытка через ${delay}мс... (осталось попыток: ${retries})`);
                contentDiv.innerHTML = `<div class="loading">⚠️ Ошибка: ${error.message}. Повторная попытка через ${delay/1000}с...</div>`;
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2;
            } else {
                console.error('Error:', error);
                contentDiv.innerHTML = `<div class="error-message">❌ Ошибка соединения с сервером: ${error.message}<br><br>Попробуйте уменьшить количество данных или обновить страницу</div>`;
            }
        }
    }
}

// Функция показа выбранного набора данных
function showDataset(datasetId) {
    currentDatasetId = datasetId;
    renderDatasetDetail(allDatasets[datasetId]);

    document.querySelectorAll('.dataset-btn').forEach((btn, idx) => {
        if (idx == datasetId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Функция отображения деталей набора данных
function renderDatasetDetail(dataset) {
    if (!dataset) return;

    const viz = dataset.viz || {};
    const detailHtml = `
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Всего запросов</div><div class="stat-value">${dataset.total_requests || 0}</div></div>
            <div class="stat-card"><div class="stat-label">✅ OK</div><div class="stat-value" style="color:#27ae60">${dataset.ok || 0}</div></div>
            <div class="stat-card"><div class="stat-label">⚠️ LIMIT</div><div class="stat-value" style="color:#f39c12">${dataset.limited || 0}</div></div>
            <div class="stat-card"><div class="stat-label">🔴 BLOCK</div><div class="stat-value" style="color:#e74c3c">${dataset.blocked || 0}</div></div>
            <div class="stat-card"><div class="stat-label">Средняя частота</div><div class="stat-value">${dataset.avg_rate || 0}</div></div>
            <div class="stat-card"><div class="stat-label">Пиковая частота</div><div class="stat-value">${dataset.max_rate || 0}</div></div>
            <div class="stat-card"><div class="stat-label">Мин. частота</div><div class="stat-value">${dataset.min_rate || 0}</div></div>
            <div class="stat-card"><div class="stat-label">Всего сообщений</div><div class="stat-value">${dataset.total_messages || 0}</div></div>
        </div>

        <div class="visualizations">
            <div class="viz-card"><h3>📈 Динамика частоты обмена</h3>${viz.rate_line ? `<img src="${viz.rate_line}" alt="График частоты">` : '<p>Нет данных</p>'}</div>
            <div class="viz-card"><h3>📊 Количество сообщений</h3>${viz.messages_bar ? `<img src="${viz.messages_bar}" alt="График сообщений">` : '<p>Нет данных</p>'}</div>
            <div class="viz-card"><h3>🥧 Распределение статусов</h3>${viz.status_pie ? `<img src="${viz.status_pie}" alt="Круговая диаграмма">` : '<p>Нет данных</p>'}</div>
        </div>

        <div class="table-container">
            <h3>📋 Детальная таблица запросов</h3>
            <div style="overflow-x: auto; max-height: 500px;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Сообщений</th>
                            <th>Время(сек)</th>
                            <th>Частота</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>${dataset.table_rows || '<tr><td colspan="5">Нет данных</td></tr>'}</tbody>
                </table>
            </div>
        </div>
    `;
    document.getElementById('dataset-detail').innerHTML = detailHtml;
}

// Функция отображения всей страницы
function renderHTML(data) {
    if (!data.datasets || data.datasets.length === 0) {
        document.getElementById('content').innerHTML = '<div class="error-message">Нет данных для отображения</div>';
        return;
    }

    let navHtml = '<div class="dataset-nav"><strong style="align-self:center;">📁 Выберите набор данных:</strong>';
    data.datasets.forEach((dataset, idx) => {
        const activeClass = idx === 0 ? 'active' : '';
        navHtml += `<button class="dataset-btn ${activeClass}" onclick="showDataset(${idx})">
            📊 ${dataset.dataset_name}
        </button>`;
    });
    navHtml += '</div>';

    const totalStats = data.total_stats || {};
    const comparisonViz = data.comparison_viz || {};

    const html = `
        ${navHtml}

        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Всего наборов</div><div class="stat-value">${totalStats.total_datasets || 0}</div></div>
            <div class="stat-card"><div class="stat-label">Всего запросов</div><div class="stat-value">${totalStats.total_requests || 0}</div></div>
            <div class="stat-card"><div class="stat-label">✅ Всего OK</div><div class="stat-value" style="color:#27ae60">${totalStats.total_ok || 0}</div></div>
            <div class="stat-card"><div class="stat-label">⚠️ Всего LIMIT</div><div class="stat-value" style="color:#f39c12">${totalStats.total_limited || 0}</div></div>
            <div class="stat-card"><div class="stat-label">🔴 Всего BLOCK</div><div class="stat-value" style="color:#e74c3c">${totalStats.total_blocked || 0}</div></div>
            <div class="stat-card"><div class="stat-label">Общая средняя частота</div><div class="stat-value">${totalStats.total_avg_rate || 0}</div></div>
        </div>

        <div class="comparison-section">
            <h2>📊 Сравнительный анализ всех наборов данных</h2>
            <div class="visualizations">
                <div class="viz-card"><h3>📈 Сравнение частоты обмена</h3>${comparisonViz.comparison_line ? `<img src="${comparisonViz.comparison_line}" alt="Сравнение частоты">` : '<p>Нет данных</p>'}</div>
                <div class="viz-card"><h3>📊 Количество заблокированных сообщений к общему числу</h3>
                    <p style="font-size:12px; color:#666; margin-bottom:10px;">🔵 Синий = все сообщения | 🔴 Красный = заблокированные сообщения</p>
                    ${comparisonViz.messages_vs_blocked ? `<img src="${comparisonViz.messages_vs_blocked}" alt="Сравнение сообщений">` : '<p>Нет данных</p>'}
                </div>
                <div class="viz-card"><h3>📊 Доля заблокированных сообщений</h3>
                    <p style="font-size:12px; color:#666; margin-bottom:10px;">Процент сообщений, которые были заблокированы</p>
                    ${comparisonViz.blocked_percentage ? `<img src="${comparisonViz.blocked_percentage}" alt="Процент блокировок">` : '<p>Нет данных</p>'}
                </div>
                <div class="viz-card"><h3>📉 Средняя частота обмена</h3>
                    <p style="font-size:12px; color:#666; margin-bottom:10px;">🟢 Зеленый = норма | 🔴 Красный = превышение порога (${maxRate})</p>
                    ${comparisonViz.comparison_horizontal ? `<img src="${comparisonViz.comparison_horizontal}" alt="Средняя частота">` : '<p>Нет данных</p>'}
                </div>
            </div>
        </div>

        <h2 style="margin: 30px 0 20px 0; padding-bottom: 10px; border-bottom: 3px solid #667eea;">🔍 Детальный анализ выбранного набора</h2>
        <div id="dataset-detail"></div>
    `;

    document.getElementById('content').innerHTML = html;

    if (data.datasets.length > 0) {
        renderDatasetDetail(data.datasets[0]);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    maxRate = parseInt(document.body.dataset.maxRate) || 100;
    refreshData();
});