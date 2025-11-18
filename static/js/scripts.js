document.addEventListener('DOMContentLoaded', function() {
    
    var inputs = document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="hidden"])');
    inputs.forEach(function(input) {
        input.classList.add('form-control');
    });

    var selects = document.querySelectorAll('select');
    selects.forEach(function(select) {
        select.classList.add('form-select');
    });

    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 4000); 
    });

});