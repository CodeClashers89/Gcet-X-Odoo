document.addEventListener('DOMContentLoaded', () => {
    const statusChartCanvas = document.getElementById('statusChart');
    const typeChartCanvas = document.getElementById('typeChart');
    const statusEl = document.getElementById('approvalStatusCounts');
    const typeEl = document.getElementById('approvalTypeStats');

    if (!statusChartCanvas || !typeChartCanvas || !statusEl || !typeEl) {
        return;
    }

    const statusData = JSON.parse(statusEl.textContent);
    const typeData = JSON.parse(typeEl.textContent);

    const statusCtx = statusChartCanvas.getContext('2d');
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: ['Approved', 'Rejected', 'Pending'],
            datasets: [{
                data: statusData,
                backgroundColor: ['#28A745', '#DC3545', '#FFC107'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    const typeLabels = typeData.map((t) => (t.request_type === 'quotation' ? 'Quotations' : 'Orders'));
    const typeCounts = typeData.map((t) => t.count);

    const typeCtx = typeChartCanvas.getContext('2d');
    new Chart(typeCtx, {
        type: 'bar',
        data: {
            labels: typeLabels,
            datasets: [{
                label: 'Requests',
                data: typeCounts,
                backgroundColor: ['#17A2B8', '#007BFF'],
                borderColor: ['#0C5460', '#0056B3'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
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
