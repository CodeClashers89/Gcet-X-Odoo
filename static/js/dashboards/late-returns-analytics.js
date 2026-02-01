document.addEventListener('DOMContentLoaded', () => {
    const lateDataEl = document.getElementById('lateReturnsData');
    const totalReturnsEl = document.getElementById('totalReturnsValue');
    const lateReturnsEl = document.getElementById('lateReturnsValue');
    const lateChartCanvas = document.getElementById('lateReturnsChart');
    const statusChartCanvas = document.getElementById('statusChart');

    if (!lateDataEl || !totalReturnsEl || !lateReturnsEl || !lateChartCanvas || !statusChartCanvas) {
        return;
    }

    const lateData = JSON.parse(lateDataEl.textContent);
    const totalReturns = JSON.parse(totalReturnsEl.textContent);
    const lateReturns = JSON.parse(lateReturnsEl.textContent);

    const lateLabels = lateData.map((d) => new Date(d.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));
    const lateCounts = lateData.map((d) => d.count);

    const lateCtx = lateChartCanvas.getContext('2d');
    new Chart(lateCtx, {
        type: 'bar',
        data: {
            labels: lateLabels,
            datasets: [{
                label: 'Late Returns',
                data: lateCounts,
                backgroundColor: 'rgba(220, 53, 69, 0.7)',
                borderColor: '#DC3545',
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

    const onTimeCount = totalReturns - lateReturns;
    const statusCtx = statusChartCanvas.getContext('2d');
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: ['On Time', 'Late'],
            datasets: [{
                data: [onTimeCount, lateReturns],
                backgroundColor: ['#28A745', '#DC3545'],
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
