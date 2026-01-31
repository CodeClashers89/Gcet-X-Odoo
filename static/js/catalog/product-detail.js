document.addEventListener('DOMContentLoaded', () => {
    const resultDiv = document.getElementById('availabilityResult');
    const checkButton = document.getElementById('checkAvailabilityBtn');
    const startDateInput = document.getElementById('checkStartDate');
    const endDateInput = document.getElementById('checkEndDate');
    const quantityInput = document.getElementById('checkQuantity');

    if (!resultDiv || !checkButton || !startDateInput || !endDateInput || !quantityInput) {
        return;
    }

    const productId = resultDiv.dataset.productId;
    const availabilityUrl = resultDiv.dataset.availabilityUrl;

    const checkAvailability = () => {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const quantity = quantityInput.value;

        if (!startDate || !endDate) {
            alert('Please select both start and end dates');
            return;
        }

        resultDiv.className = 'availability-result';
        resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking availability...';

        fetch(`${availabilityUrl}?product_id=${productId}&start_date=${startDate}&end_date=${endDate}&quantity=${quantity}`)
            .then((response) => response.json())
            .then((data) => {
                if (data.available) {
                    resultDiv.className = 'availability-result success';
                    let html = `<strong><i class="fas fa-check-circle"></i> ${data.message}</strong>`;
                    if (data.pricing && data.pricing.daily_price) {
                        html += `<br><small>₹${data.pricing.daily_price} per day × ${data.pricing.duration_days} days = ₹${data.pricing.total_price}</small>`;
                    }
                    resultDiv.innerHTML = html;
                } else {
                    resultDiv.className = 'availability-result error';
                    resultDiv.innerHTML = `<strong><i class="fas fa-times-circle"></i> ${data.message}</strong>`;
                }
            })
            .catch((error) => {
                resultDiv.className = 'availability-result error';
                resultDiv.innerHTML = '<strong><i class="fas fa-times-circle"></i> Error checking availability</strong>';
                console.error('Error:', error);
            });
    };

    checkButton.addEventListener('click', checkAvailability);

    quantityInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            checkAvailability();
        }
    });
});
