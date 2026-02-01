document.addEventListener('DOMContentLoaded', () => {
    const trendCanvas = document.getElementById('trendChart');
    const statusCanvas = document.getElementById('statusChart');
    const labelsEl = document.getElementById('orderChartLabels');
    const dataEl = document.getElementById('orderChartData');
    const statusEl = document.getElementById('orderStatusStats');

    if (!trendCanvas || !statusCanvas || !labelsEl || !dataEl || !statusEl) {
        return;
    }

    const labels = JSON.parse(labelsEl.textContent);
    const data = JSON.parse(dataEl.textContent);
    const statusData = JSON.parse(statusEl.textContent);

    const trendCtx = trendCanvas.getContext('2d');
    new Chart(trendCtx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Orders Created',
                data,
                backgroundColor: 'rgba(33, 150, 243, 0.7)',
                borderColor: '#2196F3',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    const statusLabels = statusData.map((s) => s.status.charAt(0).toUpperCase() + s.status.slice(1));
    const statusCounts = statusData.map((s) => s.count);

    const statusCtx = statusCanvas.getContext('2d');
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: statusLabels,
            datasets: [{
                data: statusCounts,
                backgroundColor: [
                    '#6C757D',
                    '#17A2B8',
                    '#FFC107',
                    '#28A745',
                    '#DC3545'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
});
