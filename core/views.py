from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from gestion.models import Producto
from .carrito import Carrito

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
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario) # Logueamos al usuario automáticamente al registrarse
            return redirect('core:home')
    else:
        form = UserCreationForm()
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