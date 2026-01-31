document.addEventListener('DOMContentLoaded', () => {
    const gstinInput = document.getElementById('id_gstin');
    const statusDiv = document.getElementById('gstin-status');

    if (!gstinInput || !statusDiv) {
        return;
    }

    const verifyUrl = statusDiv.dataset.verifyUrl || '/accounts/api/verify-gstin/';

    gstinInput.addEventListener('blur', () => {
        const gstin = gstinInput.value.toUpperCase();

        if (gstin.length !== 15) {
            statusDiv.innerHTML = '<span style="color: #ffc107;">GSTIN must be 15 characters</span>';
            return;
        }

        statusDiv.innerHTML = '<span style="color: #17a2b8;">Verifying GSTIN...</span>';

        // Helper to set field value and read-only state
        const setField = (id, value, isReadOnly = true) => {
            const field = document.getElementById(id);
            if (field) {
                field.value = value || '';
                if (isReadOnly && value) {
                    field.setAttribute('readonly', 'readonly');
                    field.style.backgroundColor = '#e9ecef';
                    field.style.cursor = 'not-allowed';

                    // Add auto-filled label if not exists
                    let label = field.parentNode.querySelector('.auto-filled-label');
                    if (!label) {
                        label = document.createElement('span');
                        label.className = 'auto-filled-label';
                        label.style.fontSize = '11px';
                        label.style.color = '#28a745';
                        label.style.marginLeft = '10px';
                        label.innerHTML = '<i class="fas fa-check-circle"></i> Auto-filled from GSTIN';
                        field.parentNode.querySelector('label').appendChild(label);
                    }
                } else {
                    field.removeAttribute('readonly');
                    field.style.backgroundColor = '';
                    field.style.cursor = '';
                    // Remove label
                    const label = field.parentNode.querySelector('.auto-filled-label');
                    if (label) label.remove();
                }
            }
        };

        fetch(`${verifyUrl}?gstin=${gstin}`)
            .then((response) => response.json())
            .then((data) => {
                if (data.valid) {
                    statusDiv.innerHTML = `<span style="color: #28a745;">✓ Valid - ${data.company_name}</span>`;

                    // Auto-fill fields
                    setField('id_company_name', data.company_name);
                    setField('id_business_address', data.business_address);
                    setField('id_state', data.state);
                    setField('id_city', data.city);
                    setField('id_pincode', data.pincode);

                } else {
                    statusDiv.innerHTML = `<span style="color: #dc3545;">✗ ${data.message}</span>`;

                    // Unlock fields if invalid
                    setField('id_company_name', '', false);
                    setField('id_business_address', '', false);
                    setField('id_state', '', false);
                    setField('id_city', '', false);
                    setField('id_pincode', '', false);
                }
            })
            .catch((error) => {
                statusDiv.innerHTML = '<span style="color: #dc3545;">Verification error. Check manually.</span>';
                console.error(error);
                // Unlock fields on error
                setField('id_company_name', '', false);
                setField('id_business_address', '', false);
                setField('id_state', '', false);
                setField('id_city', '', false);
                setField('id_pincode', '', false);
            });
    });
});
