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

        fetch(`${verifyUrl}?gstin=${gstin}`)
            .then((response) => response.json())
            .then((data) => {
                if (data.valid) {
                    statusDiv.innerHTML = `<span style="color: #28a745;">✓ Valid - ${data.company_name}</span>`;
                } else {
                    statusDiv.innerHTML = `<span style="color: #dc3545;">✗ ${data.message}</span>`;
                }
            })
            .catch((error) => {
                statusDiv.innerHTML = '<span style="color: #dc3545;">Verification error. Check manually.</span>';
                console.error(error);
            });
    });
});
