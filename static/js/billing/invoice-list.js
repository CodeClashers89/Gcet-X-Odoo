document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('invoice-status-filter');
    if (!select) {
        return;
    }

    const baseUrl = select.dataset.baseUrl || '/billing/invoices/';

    select.addEventListener('change', (event) => {
        const status = event.target.value;
        if (status) {
            window.location.href = `${baseUrl}?status=${encodeURIComponent(status)}`;
        } else {
            window.location.href = baseUrl;
        }
    });
});
