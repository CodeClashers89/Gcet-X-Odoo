document.addEventListener('DOMContentLoaded', () => {
    const chartCanvas = document.getElementById('trendChart');
    const labelsEl = document.getElementById('quotationChartLabels');
    const dataEl = document.getElementById('quotationChartData');

    if (!chartCanvas || !labelsEl || !dataEl) {
        return;
    }

    const labels = JSON.parse(labelsEl.textContent);
    const data = JSON.parse(dataEl.textContent);
    const trendCtx = chartCanvas.getContext('2d');

    new Chart(trendCtx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Quotations Created',
                data,
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6,
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
});
