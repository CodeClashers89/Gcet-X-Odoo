document.addEventListener('DOMContentLoaded', () => {
    const chartCanvas = document.getElementById('revenueChart');
    const labelsEl = document.getElementById('revenueChartLabels');
    const dataEl = document.getElementById('revenueChartData');

    if (!chartCanvas || !labelsEl || !dataEl) {
        return;
    }

    const labels = JSON.parse(labelsEl.textContent);
    const data = JSON.parse(dataEl.textContent);
    const revenueCtx = chartCanvas.getContext('2d');

    new Chart(revenueCtx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Daily Revenue',
                data,
                borderColor: '#28A745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointRadius: 5,
                pointBackgroundColor: '#28A745',
                pointHoverRadius: 7,
            }]
        },
        options: {
            responsive: true,
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
                        callback: (value) => `₹${value.toLocaleString('en-IN')}`
                    }
                }
            }
        }
    });
});
