document.addEventListener('click', (event) => {
    const confirmElement = event.target.closest('[data-confirm]');
    if (!confirmElement) {
        return;
    }

    const message = confirmElement.dataset.confirm || 'Are you sure?';
    if (!window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
    }
});
