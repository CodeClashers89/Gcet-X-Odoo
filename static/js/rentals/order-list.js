document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('order-status-filter');
    if (!select) {
        return;
    }

    const baseUrl = select.dataset.baseUrl || '/rentals/order/list/';

    select.addEventListener('change', (event) => {
        const status = event.target.value;
        if (status) {
            window.location.href = `${baseUrl}?status=${encodeURIComponent(status)}`;
        } else {
            window.location.href = baseUrl;
        }
    });
});
