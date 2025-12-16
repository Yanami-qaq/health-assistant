/* app/static/js/dashboard.js */

function toggleTask(planId, taskIdx, element) {
    element.classList.toggle('completed');
    fetch('/plan/toggle_task', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ plan_id: planId, task_idx: taskIdx })
    }).then(res => res.json())
      .then(data => {
          if(data.status !== 'success') {
              element.classList.toggle('completed');
              alert('同步失败，请检查网络');
          }
      });
}

document.addEventListener('DOMContentLoaded', () => {
    const planEl = document.getElementById('plan-markdown');
    if (planEl) planEl.innerHTML = marked.parse(planEl.textContent);
});

function initDashboardCharts(data) {
    Chart.defaults.font.family = "'Nunito', sans-serif";
    Chart.defaults.color = '#6c757d';

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { boxWidth: 8, usePointStyle: true } } },
        scales: { x: { grid: { display: false } }, y: { grid: { borderDash: [5,5] } } }
    };

    if (document.getElementById('mainChart')) {
        new Chart(document.getElementById('mainChart'), {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    { label: '体重 (kg)', data: data.weights, borderColor: '#ff6b6b', backgroundColor: 'rgba(255, 107, 107, 0.1)', yAxisID: 'y', tension: 0.4, fill: true },
                    { label: '步数', data: data.steps, borderColor: '#4dabf7', backgroundColor: 'rgba(77, 171, 247, 0.1)', yAxisID: 'y1', tension: 0.4, fill: true }
                ]
            },
            options: {
                ...commonOptions,
                interaction: { mode: 'index', intersect: false },
                scales: { y: { display: true, position: 'left' }, y1: { display: true, position: 'right', grid: { display: false } } }
            }
        });
    }

    if (document.getElementById('bodySleepChart')) {
        new Chart(document.getElementById('bodySleepChart'), {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    { label: '体脂%', data: data.bodyFats, borderColor: '#fdcb6e', yAxisID: 'y', tension: 0.4 },
                    { label: '睡眠(h)', data: data.sleepHours, borderColor: '#a29bfe', yAxisID: 'y1', type: 'bar', backgroundColor: '#a29bfe', borderRadius: 3 }
                ]
            },
            options: { ...commonOptions, scales: { y: { display: true }, y1: { display: true, position: 'right', grid: { display: false } } } }
        });
    }

    if (document.getElementById('waterChart')) {
        new Chart(document.getElementById('waterChart'), {
            type: 'bar',
            data: {
                labels: data.dates,
                datasets: [{ label: '毫升', data: data.waterIntakes, backgroundColor: '#00cec9', borderRadius: 4 }]
            },
            options: { ...commonOptions, plugins: { legend: { display: false } } }
        });
    }

    if (document.getElementById('cardioChart')) {
        new Chart(document.getElementById('cardioChart'), {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    { label: '心率', data: data.heartRates, borderColor: '#ff7675', tension: 0.4, pointRadius: 1 },
                    { label: '血糖', data: data.bloodGlucoses, borderColor: '#6c5ce7', borderDash: [3,3], tension: 0.4, pointRadius: 3 }
                ]
            },
            options: commonOptions
        });
    }
}