document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Estilos para Inputs
    var inputs = document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="hidden"])');
    inputs.forEach(function(input) {
        input.classList.add('form-control');
    });

    // 2. Estilos para Selects
    var selects = document.querySelectorAll('select');
    selects.forEach(function(select) {
        select.classList.add('form-select');
    });

    // 3. Auto-cierre de alertas
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 10000); 
    });

    // ---------------------------------------------------------
    // 4. LÓGICA DE BANDERAS (CORREGIDA)
    // ---------------------------------------------------------
    
    // CAMBIO IMPORTANTE: Usamos querySelector buscando por el nombre "codigo_pais"
    var selectPais = document.querySelector('select[name="codigo_pais"]'); 
    
    if (selectPais) {
        console.log("¡Selector de país encontrado! Aplicando banderas..."); // Mensaje de control para saber si funciona

        var mapaBanderas = {
            '+569': 'cl',
            '+54':  'ar',
            '+51':  'pe',
            '+57':  'co'
        };

        // Crear la bandera
        var flagSpan = document.createElement('span');
        flagSpan.className = 'input-group-text'; 
        flagSpan.innerHTML = '<span class="fi fi-cl"></span>'; 

        // Crear el contenedor (wrapper) estilo Bootstrap
        var parent = selectPais.parentNode;
        var wrapper = document.createElement('div');
        wrapper.className = 'input-group';
        
        // Mover los elementos dentro del grupo
        parent.replaceChild(wrapper, selectPais);
        wrapper.appendChild(flagSpan);
        wrapper.appendChild(selectPais);

        // Evento: Cambiar bandera al seleccionar otro país
        selectPais.addEventListener('change', function() {
            var codigo = this.value;
            var paisIso = mapaBanderas[codigo] || 'xx';
            flagSpan.innerHTML = '<span class="fi fi-' + paisIso + '"></span>';
        });

        // Inicializar (por si ya viene uno seleccionado)
        selectPais.dispatchEvent(new Event('change'));
    } else {
        console.log("No se encontró el selector de país en esta página.");
    }
});