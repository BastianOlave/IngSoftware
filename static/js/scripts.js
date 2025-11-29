/* --- static/js/scripts.js --- */

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Estilos automáticos para Inputs de Django
    var inputs = document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="hidden"])');
    inputs.forEach(function(input) {
        input.classList.add('form-control');
    });

    var selects = document.querySelectorAll('select');
    selects.forEach(function(select) {
        select.classList.add('form-select');
    });

    // 2. Auto-cierre de alertas (10 segundos)
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 10000); 
    });

    // ---------------------------------------------------------
    // 3. LÓGICA DE BANDERAS (Checkout)
    // ---------------------------------------------------------
    var selectPais = document.querySelector('select[name="codigo_pais"]'); 
    
    if (selectPais) {
        console.log("¡Selector de país encontrado! Aplicando banderas...");

        var mapaBanderas = {
            '+569': 'cl',
            '+54':  'ar',
            '+51':  'pe',
            '+57':  'co'
        };

        // Crear la bandera visual
        var flagSpan = document.createElement('span');
        flagSpan.className = 'input-group-text'; 
        flagSpan.innerHTML = '<span class="fi fi-cl"></span>'; 

        // Crear el contenedor (wrapper)
        var parent = selectPais.parentNode;
        var wrapper = document.createElement('div');
        wrapper.className = 'input-group';
        
        // Mover los elementos
        parent.replaceChild(wrapper, selectPais);
        wrapper.appendChild(flagSpan);
        wrapper.appendChild(selectPais);

        // Evento al cambiar
        selectPais.addEventListener('change', function() {
            var codigo = this.value;
            var paisIso = mapaBanderas[codigo] || 'xx';
            flagSpan.innerHTML = '<span class="fi fi-' + paisIso + '"></span>';
        });

        // Inicializar
        selectPais.dispatchEvent(new Event('change'));
    }

    // ---------------------------------------------------------
    // 4. VALIDACIÓN DE TELÉFONO (8 Dígitos y Solo Números)
    // ---------------------------------------------------------
    var inputTelefono = document.getElementById('input-telefono');
    
    if (inputTelefono) {
        // Crear el mensaje de error
        var mensajeLimite = document.createElement('small');
        mensajeLimite.style.color = 'red';
        mensajeLimite.style.display = 'none';
        mensajeLimite.innerText = '¡Límite de 8 números alcanzado!';
        
        // Insertar mensaje después del input (o del input-group si existiera)
        inputTelefono.parentNode.appendChild(mensajeLimite);

        inputTelefono.addEventListener('input', function() {
            // Eliminar cualquier caracter que no sea número
            this.value = this.value.replace(/[^0-9]/g, '');

            // Mostrar mensaje si llega a 8
            if (this.value.length >= 8) {
                mensajeLimite.style.display = 'block';
            } else {
                mensajeLimite.style.display = 'none';
            }
        });
    }
});

// ---------------------------------------------------------
// 5. FUNCIONES GLOBALES DEL CARRITO (Para usar onclick en HTML)
// ---------------------------------------------------------

function validarYEnviar(input, idProducto, nombreProducto) {
    var cantidad = parseInt(input.value);
    var form = document.getElementById('form-' + idProducto);

    if (cantidad === 0) {
        var confirmar = confirm("¿Estás seguro que deseas eliminar '" + nombreProducto + "' del carrito?");
        if (confirmar) {
            form.submit(); 
        } else {
            input.value = 1; 
        }
    } else if (cantidad < 0) {
        alert("La cantidad no puede ser negativa.");
        input.value = 1;
    } else {
        form.submit();
    }
}

function confirmarEliminar(url, nombreProducto) {
    var confirmar = confirm("¿Estás seguro que deseas eliminar '" + nombreProducto + "'?");
    if (confirmar) {
        window.location.href = url;
    }
}