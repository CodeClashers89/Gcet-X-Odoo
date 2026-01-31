document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('formset-container');
    if (!container) {
        return;
    }

    const addButton = document.getElementById('add-formset');
    const formCount = document.getElementById('id_quotationline_set-TOTAL_FORMS');
    const emptyForm = document.querySelector('.formset-row.empty-form');

    const applyFormClasses = (root) => {
        root.querySelectorAll('select, input').forEach((input) => {
            if (input.tagName === 'SELECT' || input.tagName === 'INPUT') {
                input.classList.add('form-control', 'form-select');
            }
        });
    };

    document.querySelectorAll('[id^="id_quotationline_set-"]').forEach((input) => {
        if (input.tagName === 'SELECT' || input.tagName === 'INPUT') {
            input.classList.add('form-control', 'form-select');
        }
    });

    if (addButton && emptyForm && formCount) {
        addButton.addEventListener('click', () => {
            const newForm = emptyForm.cloneNode(true);
            newForm.classList.remove('empty-form');
            newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, formCount.value);

            container.appendChild(newForm);
            formCount.value = parseInt(formCount.value, 10) + 1;

            applyFormClasses(newForm);
        });
    }

    container.addEventListener('click', (event) => {
        const removeButton = event.target.closest('.remove-row');
        if (!removeButton) {
            return;
        }

        const row = removeButton.closest('.formset-row');
        if (!row) {
            return;
        }

        const deleteCheckbox = row.querySelector('[id$="-DELETE"]');
        if (deleteCheckbox) {
            deleteCheckbox.checked = true;
            row.style.display = 'none';
        }
    });
});
