document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('return-form');
    if (!form) {
        return;
    }

    const checkboxId = form.dataset.damageCheckboxId;
    const damageCheckbox = checkboxId ? document.getElementById(checkboxId) : null;
    const damageSection = document.getElementById('damage-section');

    if (!damageCheckbox || !damageSection) {
        return;
    }

    const toggleDamageSection = () => {
        damageSection.style.display = damageCheckbox.checked ? 'block' : 'none';
    };

    damageCheckbox.addEventListener('change', toggleDamageSection);
    toggleDamageSection();
});
