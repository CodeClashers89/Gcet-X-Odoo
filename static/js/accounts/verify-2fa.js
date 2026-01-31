document.addEventListener('DOMContentLoaded', () => {
    const tokenInput = document.getElementById('token');
    if (!tokenInput) {
        return;
    }

    tokenInput.addEventListener('input', (event) => {
        if (event.target.value.length === 6) {
            setTimeout(() => {
                event.target.form.submit();
            }, 300);
        }
    });

    tokenInput.addEventListener('keypress', (event) => {
        if (!/[0-9]/.test(event.key) && event.key !== 'Backspace' && event.key !== 'Delete') {
            event.preventDefault();
        }
    });
});
