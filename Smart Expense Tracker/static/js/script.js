// Smart Expense Splitter JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Flash message auto-dismiss
    setTimeout(function() {
        var flashMessages = document.querySelectorAll('.alert-dismissible');
        flashMessages.forEach(function(message) {
            var alert = new bootstrap.Alert(message);
            alert.close();
        });
    }, 5000);

    // Product form - Select all members checkbox
    var selectAllCheckbox = document.getElementById('select-all-members');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            var memberCheckboxes = document.querySelectorAll('input[name="members"]');
            memberCheckboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllCheckbox.checked;
            });
        });
    }

    // Bill summary - Toggle transaction details
    var toggleTransactionBtn = document.getElementById('toggle-transactions');
    if (toggleTransactionBtn) {
        toggleTransactionBtn.addEventListener('click', function() {
            var transactionDetails = document.getElementById('transaction-details');
            if (transactionDetails.classList.contains('d-none')) {
                transactionDetails.classList.remove('d-none');
                toggleTransactionBtn.innerHTML = '<i class="fas fa-chevron-up me-1"></i> Hide Details';
            } else {
                transactionDetails.classList.add('d-none');
                toggleTransactionBtn.innerHTML = '<i class="fas fa-chevron-down me-1"></i> Show Details';
            }
        });
    }

    // Dashboard - Group card hover effect
    var groupCards = document.querySelectorAll('.group-card');
    groupCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-lg');
        });
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-lg');
        });
    });

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Price input formatting
    var priceInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    priceInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });

    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                event.preventDefault();
            }
        });
    });
});