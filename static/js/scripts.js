document.addEventListener('DOMContentLoaded', function() {

    var inputs = document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="hidden"])');
    inputs.forEach(function(input) {
        input.classList.add('form-control');
    });

    var selects = document.querySelectorAll('select');
    selects.forEach(function(select) {
        select.classList.add('form-select');
    });

    var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 10000);
    });

    var selectPais = document.querySelector('select[name="codigo_pais"]');

    if (selectPais && !selectPais.parentNode.classList.contains('input-group')) {
        var mapaBanderas = {
            '+569': 'cl',
            '+54': 'ar',
            '+51': 'pe',
            '+57': 'co'
        };

        var flagSpan = document.createElement('span');
        flagSpan.className = 'input-group-text';
        flagSpan.innerHTML = '<span class="fi fi-cl"></span>';

        var parent = selectPais.parentNode;
        var wrapper = document.createElement('div');
        wrapper.className = 'input-group';

        parent.replaceChild(wrapper, selectPais);
        wrapper.appendChild(flagSpan);
        wrapper.appendChild(selectPais);

        selectPais.addEventListener('change', function() {
            var codigo = this.value;
            var paisIso = mapaBanderas[codigo] || 'xx';
            flagSpan.innerHTML = '<span class="fi fi-' + paisIso + '"></span>';
        });

        selectPais.dispatchEvent(new Event('change'));
    }

    var inputTelefono = document.getElementById('input-telefono');

    if (inputTelefono) {
        var mensajeLimite = document.createElement('small');
        mensajeLimite.style.color = 'red';
        mensajeLimite.style.display = 'none';
        mensajeLimite.innerText = '¡Límite de 8 números alcanzado!';

        inputTelefono.parentNode.appendChild(mensajeLimite);

        inputTelefono.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');

            if (this.value.length >= 8) {
                mensajeLimite.style.display = 'block';
            } else {
                mensajeLimite.style.display = 'none';
            }
        });
    }

    var passwordInputs = document.querySelectorAll('input[type="password"]');

    passwordInputs.forEach(function(input) {
        var wrapper = document.createElement('div');
        wrapper.className = 'input-group';

        input.parentNode.insertBefore(wrapper, input);

        wrapper.appendChild(input);

        var button = document.createElement('button');
        button.className = 'btn btn-outline-secondary';
        button.type = 'button';
        button.style.borderTopRightRadius = "0.375rem";
        button.style.borderBottomRightRadius = "0.375rem";
        button.innerHTML = '<i class="bi bi-eye"></i>';

        button.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                button.innerHTML = '<i class="bi bi-eye-slash"></i>';
            } else {
                input.type = 'password';
                button.innerHTML = '<i class="bi bi-eye"></i>';
            }
        });

        wrapper.appendChild(button);
    });

    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('rut-input')) {
            let rut = e.target.value.replace(/[^0-9kK]/g, '').toUpperCase();

            if (rut.length > 1) {
                const cuerpo = rut.slice(0, -1);
                const dv = rut.slice(-1);
                e.target.value = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + "-" + dv;
            } else {
                e.target.value = rut;
            }
        }
    });

});

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

async function validarDireccion(forzado = false) {
    const direccionInput = document.getElementById("id_direccion");
    const comunaInput = document.getElementById("id_comuna");
    const postalInput = document.getElementById("id_codigo_postal");

    const direccion = direccionInput.value.trim();
    const comuna = comunaInput.value.trim();
    const postal = postalInput.value.trim();

    let query = "";

    if (direccion) query += direccion;
    if (comuna) query += (query ? ", " : "") + comuna;
    if (postal) query += (query ? ", " : "") + postal;
    query += ", Chile";

    if (!query.replace(", Chile", "").trim()) {
        if (forzado)
            alert("Debes ingresar al menos Dirección, Comuna o Código Postal");
        return;
    }

    const apiKey = "f01f935c76bd4bf4aa61ba170308c61b";
    const url = `https://api.geoapify.com/v1/geocode/search?text=${encodeURIComponent(query)}&apiKey=${apiKey}`;

    try {
        const resp = await fetch(url);
        const data = await resp.json();

        let alerta = document.getElementById("alerta");
        if (!alerta) {
            alerta = document.createElement("div");
            alerta.id = "alerta";
            alerta.className = "mt-2 small fw-bold";
            direccionInput.parentNode.appendChild(alerta);
        }

        if (!data.features || !data.features.length) {
            alerta.innerHTML = "❌ Dirección / comuna / código postal no válidos";
            alerta.style.color = "red";
            return false;
        }

        const info = data.features[0].properties;

        alerta.innerHTML = `
            ✔ Dirección encontrada: <br>
            <span class="text-muted">${info.formatted}</span>
        `;
        alerta.style.color = "green";

        if (info.city && !comunaInput.value) comunaInput.value = info.city;
        if (info.postcode && !postalInput.value) postalInput.value = info.postcode;

        return true;
    } catch (error) {
        console.error("Error validando dirección:", error);
        return false;
    }
}