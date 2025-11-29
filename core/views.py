from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
import time

# Transbank
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_type import IntegrationType

from gestion.models import Producto, Cliente, Pedido, DetallePedido
from .carrito import Carrito
from .forms import DatosEnvioForm, RegistroClienteForm, PerfilUsuarioForm

# --- VISTAS GENERALES ---

def home(request):
    productos_destacados = Producto.objects.all()[:4]
    return render(request, 'core/home.html', {'productos': productos_destacados})

def catalogo(request):
    productos_list = Producto.objects.all().order_by('id')
    paginator = Paginator(productos_list, 6) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/catalogo.html', {'page_obj': page_obj})

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'core/detalle.html', {'producto': producto})

# --- CARRITO ---

def agregar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    cantidad = int(request.POST.get('cantidad', 1))
    
    if cantidad > producto.stock:
        messages.error(request, f"No puedes agregar {cantidad}. Solo quedan {producto.stock}.")
        return redirect('core:detalle', producto_id=producto_id)
    
    carrito.agregar(producto=producto, cantidad=cantidad)
    return redirect('core:ver_carrito')

def actualizar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except ValueError:
        cantidad = 1

    if cantidad == 0:
        carrito.eliminar(producto)
        return redirect('core:ver_carrito')

    if cantidad > producto.stock:
        messages.error(request, f"¡Ups! Solo quedan {producto.stock} unidades de {producto.nombre}.")
        return redirect('core:ver_carrito')

    carrito.actualizar(producto, cantidad)
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

# --- USUARIOS (AUTH + PERFIL) ---

def registro(request):
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect('core:home')
    else:
        form = RegistroClienteForm()
    return render(request, 'core/registro.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        data = request.POST.copy()
        username = data.get('username')
        try:
            user_candidate = User.objects.get(username__iexact=username)
            data['username'] = user_candidate.username
        except User.DoesNotExist:
            pass 

        form = AuthenticationForm(request, data=data)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('core:home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_usuario(request):
    logout(request)
    return redirect('core:home')

@login_required
def perfil_usuario(request):
    cliente, created = Cliente.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=cliente, user=request.user)
        if form.is_valid():
            # Actualizar Auth User
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()

            # Actualizar Cliente
            cliente = form.save(commit=False)
            cliente.nombre = form.cleaned_data['first_name']
            cliente.apellido = form.cleaned_data['last_name']
            cliente.email = form.cleaned_data['email']
            
            # Unir teléfono
            codigo = form.cleaned_data['codigo_pais']
            numero = form.cleaned_data['telefono']
            cliente.telefono = f"{codigo}{numero}"
            
            # Guardar CP y resto
            cliente.codigo_postal = form.cleaned_data['codigo_postal']
            cliente.save()
            
            messages.success(request, "Tus datos han sido actualizados correctamente.")
            return redirect('core:perfil')
    else:
        form = PerfilUsuarioForm(instance=cliente, user=request.user)

    return render(request, 'core/perfil.html', {'form': form})

@login_required
def mis_pedidos(request):
    try:
        cliente = Cliente.objects.get(user=request.user)
        pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha')
    except Cliente.DoesNotExist:
        pedidos = []
    return render(request, 'core/mis_pedidos.html', {'pedidos': pedidos})

# --- PAGO (CHECKOUT + WEBPAY) ---

@login_required
def checkout(request):
    carrito = Carrito(request)
    if len(carrito) == 0:
        return redirect('core:home')

    try:
        cliente = Cliente.objects.get(user=request.user)
    except Cliente.DoesNotExist:
        if request.user.email:
            cliente, created = Cliente.objects.get_or_create(email=request.user.email, defaults={'user': request.user})
            if not created:
                cliente.user = request.user
                cliente.save()
        else:
            cliente = Cliente.objects.create(user=request.user, email="")

    if request.method == 'POST':
        form = DatosEnvioForm(request.POST, instance=cliente, user=request.user)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()

            cliente = form.save(commit=False)
            cliente.nombre = form.cleaned_data['first_name']
            cliente.apellido = form.cleaned_data['last_name']
            
            codigo = form.cleaned_data['codigo_pais']
            numero = form.cleaned_data['telefono']
            cliente.telefono = f"{codigo}{numero}"
            
            cliente.codigo_postal = form.cleaned_data['codigo_postal']
            cliente.save()

            for item in carrito.obtener_items():
                producto_bd = Producto.objects.get(id=item['producto_id'])
                if producto_bd.stock < item['cantidad']:
                    messages.error(request, f"Sin stock suficiente de {producto_bd.nombre}.")
                    return redirect('core:ver_carrito')

            pedido = Pedido.objects.create(
                cliente=cliente,
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
            
            return redirect('core:seleccion_pago', pedido_id=pedido.id)
            
    else:
        form = DatosEnvioForm(instance=cliente, user=request.user)

    return render(request, 'core/confirmar_compra.html', {
        'form': form,
        'carrito': carrito,
        'total': carrito.obtener_total_precio()
    })

def seleccion_pago(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'core/seleccion_pago.html', {'pedido': pedido})

def iniciar_pago_webpay(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    tx = Transaction(WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS, 
        IntegrationApiKeys.WEBPAY, 
        IntegrationType.TEST
    ))
    
    buy_order = f"P-{pedido.id}-{int(time.time())}"
    session_id = f"S-{request.user.id}-{int(time.time())}"
    amount = int(pedido.total)
    return_url = request.build_absolute_uri('/webpay/retorno/') 
    
    response = tx.create(buy_order, session_id, amount, return_url)
    return redirect(response['url'] + '?token_ws=' + response['token'])

def confirmar_pago_webpay(request):
    token = request.GET.get('token_ws') or request.POST.get('token_ws')
    if not token:
        messages.error(request, "Error: No se recibió token de WebPay")
        return redirect('core:home')

    try:
        tx = Transaction(WebpayOptions(
            IntegrationCommerceCodes.WEBPAY_PLUS, 
            IntegrationApiKeys.WEBPAY, 
            IntegrationType.TEST
        ))
        response = tx.commit(token)
        
        if response['response_code'] == 0:
            buy_order_completo = response['buy_order']
            pedido_id = buy_order_completo.split('-')[1]
            
            pedido = Pedido.objects.get(id=pedido_id)
            pedido.estado = 'Pagado (WebPay)'
            pedido.save()
            
            carrito = Carrito(request)
            for item in carrito.obtener_items():
                producto = get_object_or_404(Producto, id=item['producto_id'])
                producto.stock -= item['cantidad']
                producto.save()
            
            carrito.limpiar()
            messages.success(request, "¡Pago exitoso con WebPay!")
            return render(request, 'core/exito.html', {'pedido_id': pedido.id})
        else:
            messages.error(request, "El pago fue anulado o rechazado por WebPay.")
            return redirect('core:home')
    except Exception as e:
        print(f"Error Webpay: {e}")
        messages.error(request, "Ocurrió un error técnico al confirmar el pago.")
        return redirect('core:home')