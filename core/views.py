from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from gestion.models import Cliente, Pedido, DetallePedido
from django.contrib.auth import login, logout
from gestion.models import Producto
from .carrito import Carrito
from .forms import DatosEnvioForm, RegistroClienteForm


def home(request):
    productos_destacados = Producto.objects.all()[:4]
    data = {
        'productos': productos_destacados
    }
    return render(request, 'core/home.html', data)

# --- NUEVA VISTA ---
def detalle_producto(request, producto_id):
    # Buscamos el producto por su ID. Si no existe, da error 404.
    producto = get_object_or_404(Producto, id=producto_id)
    
    return render(request, 'core/detalle.html', {'producto': producto})

def agregar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Obtenemos la cantidad del formulario (por defecto 1)
    cantidad = int(request.POST.get('cantidad', 1))
    
    carrito.agregar(producto=producto, cantidad=cantidad)
    return redirect('core:ver_carrito')

def eliminar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.eliminar(producto)
    return redirect('core:ver_carrito')

def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.limpiar()
    return redirect('core:ver_carrito')

def ver_carrito(request):
    carrito = Carrito(request)
    return render(request, 'core/carrito.html', {
        'carrito': carrito,
        'total': carrito.obtener_total_precio()
    })

def registro(request):
    if request.method == 'POST':
        # Usamos el formulario nuevo
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            usuario = form.save() # Esto ejecuta el método save() que escribimos arriba
            login(request, usuario)
            return redirect('core:home')
    else:
        form = RegistroClienteForm()
    return render(request, 'core/registro.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            return redirect('core:home')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_usuario(request):
    logout(request)
    return redirect('core:home')

@login_required # <--- Obliga a iniciar sesión antes de comprar
def checkout(request):
    # 1. Validar si hay carrito
    carrito = Carrito(request)
    if len(carrito) == 0:
        return redirect('core:home')

    # 2. Obtener o crear el cliente (LÓGICA BLINDADA)
    try:
        # Opción A: Buscamos por el usuario logueado
        cliente = Cliente.objects.get(user=request.user)
    except Cliente.DoesNotExist:
        try:
            # Opción B: Si no está vinculado, buscamos por el email para no duplicar
            cliente = Cliente.objects.get(email=request.user.email)
            cliente.user = request.user # Lo vinculamos ahora
            cliente.save()
        except Cliente.DoesNotExist:
            # Opción C: Si no existe por usuario ni por email, creamos uno nuevo
            cliente = Cliente(user=request.user)
            cliente.nombre = request.user.first_name
            cliente.apellido = request.user.last_name
            cliente.email = request.user.email
            cliente.save()
    if cliente.direccion == 'Dirección pendiente':
        cliente.direccion = ''
    if cliente.telefono == 'Sin registrar':
        cliente.telefono = ''

    # 3. Procesar el Formulario
    if request.method == 'POST':
        form = DatosEnvioForm(request.POST, instance=cliente)
        if form.is_valid():
            # A) Guardamos la dirección nueva en el perfil del cliente
            cliente_actualizado = form.save()
            
            # B) CREAMOS EL PEDIDO
            pedido = Pedido.objects.create(
                cliente=cliente_actualizado,
                total=carrito.obtener_total_precio(),
                estado='Pendiente'
            )

            for item in carrito.obtener_items():
                producto = get_object_or_404(Producto, id=item['producto_id'])
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=item['cantidad'],
                    precio_unitario=item['precio']
                )

            # C) Limpiar y redirigir al éxito
            carrito.limpiar()
            return render(request, 'core/exito.html', {'pedido_id': pedido.id})
    else:
        # Si es GET, mostramos el formulario con los datos actuales
        form = DatosEnvioForm(instance=cliente)

    return render(request, 'core/confirmar_compra.html', {
        'form': form,
        'carrito': carrito,
        'total': carrito.obtener_total_precio()
    })