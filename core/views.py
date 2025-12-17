from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
import time
# Transbank
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_type import IntegrationType

from gestion.models import Producto, Cliente, Pedido, DetallePedido, Notificacion
from .carrito import Carrito
from .forms import DatosEnvioForm, RegistroClienteForm, PerfilUsuarioForm

# ---------------------------------------------------------
# VISTAS GENERALES
# ---------------------------------------------------------

def home(request):
    productos_destacados = Producto.objects.filter(stock__gt=0).order_by('-id')[:4]
    return render(request, 'core/home.html', {'productos': productos_destacados})

def catalogo(request):
    productos_list = Producto.objects.all().order_by('id')
    
    categoria_filter = request.GET.get('categoria')
    if categoria_filter:
        productos_list = productos_list.filter(categoria__icontains=categoria_filter)

    paginator = Paginator(productos_list, 6) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/catalogo.html', {'page_obj': page_obj})

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'core/detalle.html', {'producto': producto})

# ---------------------------------------------------------
# VISTAS DEL CARRITO
# ---------------------------------------------------------

def agregar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)

    cantidad = int(request.POST.get('cantidad', 1))
    
    # 1. Verificar cuánto tiene ya en el carrito
    id_str = str(producto.id)
    cantidad_en_carrito = carrito.carrito[id_str]['cantidad'] if id_str in carrito.carrito else 0
    
    # 2. Validar suma total
    if (cantidad_en_carrito + cantidad) > producto.stock:
        messages.error(request, f"No hay suficiente stock. Tienes {cantidad_en_carrito} en el carro y quedan {producto.stock}.")
        return redirect(request.META.get('HTTP_REFERER', 'core:detalle'))
    
    carrito.agregar(producto=producto, cantidad=cantidad)
    messages.success(request, f"¡{producto.nombre} agregado al carrito!")

    url_anterior = request.META.get('HTTP_REFERER')
    return redirect(url_anterior) if url_anterior else redirect('core:catalogo')

def actualizar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    try: cantidad = int(request.POST.get('cantidad', 1))
    except ValueError: cantidad = 1

    if cantidad == 0:
        carrito.eliminar(producto)
        return redirect('core:ver_carrito')

    if cantidad > producto.stock:
        messages.error(request, f"¡Ups! Solo quedan {producto.stock} unidades.")
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

# ---------------------------------------------------------
# VISTAS DE USUARIO
# ---------------------------------------------------------

def registro(request):
    if request.user.is_authenticated: return redirect('core:home')
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect('core:home')
    else: form = RegistroClienteForm()
    return render(request, 'core/registro.html', {'form': form})

def login_usuario(request):
    if request.user.is_authenticated: return redirect('core:home')
    if request.method == 'POST':
        data = request.POST.copy()
        try: data['username'] = User.objects.get(username__iexact=data.get('username')).username
        except User.DoesNotExist: pass 
        form = AuthenticationForm(request, data=data)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('core:home')
        else: messages.error(request, "Usuario o contraseña incorrectos.")
    else: form = AuthenticationForm()
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
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()

            cliente = form.save(commit=False)
            cliente.rut = form.cleaned_data['rut']
            
            num = form.cleaned_data['telefono']
            cod = form.cleaned_data['codigo_pais']
            cliente.telefono = f"{cod}{num}" if not num.startswith('+') else num
            
            cliente.save()
            messages.success(request, "Datos actualizados.")
            return redirect('core:perfil')
    else: form = PerfilUsuarioForm(instance=cliente, user=request.user)
    return render(request, 'core/perfil.html', {'form': form})

@login_required
def mis_pedidos(request):
    try:
        cliente = Cliente.objects.get(user=request.user)
        pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha')
    except Cliente.DoesNotExist: pedidos = []
    return render(request, 'core/mis_pedidos.html', {'pedidos': pedidos})

@login_required
def detalle_pedido_cliente(request, pedido_id):
    try:
        cliente = Cliente.objects.get(user=request.user)
        pedido = get_object_or_404(Pedido, id=pedido_id, cliente=cliente)
    except Cliente.DoesNotExist: return redirect('core:home')

    estado = pedido.estado
    progreso = {
        'recibido': True, 
        'pagado': 'Pagado' in estado or 'Preparacion' in estado or 'Despachado' in estado,
        'preparacion': 'Preparacion' in estado or 'Despachado' in estado,
        'despachado': 'Despachado' in estado
    }
    return render(request, 'core/detalle_pedido_cliente.html', {'pedido': pedido, 'progreso': progreso})

# ---------------------------------------------------------
# RESERVAS
# ---------------------------------------------------------

@login_required
def reservar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    try: cliente = Cliente.objects.get(user=request.user)
    except Cliente.DoesNotExist: 
        messages.error(request, "Completa tu perfil antes de reservar.")
        return redirect('core:perfil')

    # Marcamos es_reserva=True para la memoria del pedido
    pedido = Pedido.objects.create(
        cliente=cliente, 
        total=producto.precio, 
        estado='Reserva Pendiente', 
        tipo_entrega='Despacho',
        es_reserva=True 
    )
    DetallePedido.objects.create(pedido=pedido, producto=producto, cantidad=1, precio_unitario=producto.precio)

    try:
        grupo = Group.objects.get(name='Atencion al cliente')
        Notificacion.objects.create(
            destinatario_grupo=grupo, 
            pedido=pedido, 
            mensaje=f"SOLICITUD RESERVA: {cliente.nombre} solicita {producto.nombre}.", 
            estado='PENDIENTE'
        )
    except Group.DoesNotExist: pass

    messages.success(request, f"Reserva solicitada para {producto.nombre}. Te avisaremos cuando llegue.")
    return redirect('core:mis_pedidos')

# ---------------------------------------------------------
# PROCESO DE PAGO Y CHECKOUT
# ---------------------------------------------------------

@login_required
def checkout(request):
    carrito = Carrito(request)
    if len(carrito) == 0: return redirect('core:home')

    try: cliente = Cliente.objects.get(user=request.user)
    except Cliente.DoesNotExist: 
        if request.user.email: 
            cliente, _ = Cliente.objects.get_or_create(email=request.user.email, defaults={'user':request.user})
            if not _: cliente.user = request.user; cliente.save()
        else: cliente = Cliente.objects.create(user=request.user, email="")

    if request.method == 'POST':
        form = DatosEnvioForm(request.POST, instance=cliente, user=request.user)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()

            cliente = form.save(commit=False)
            cliente.rut = form.cleaned_data['rut']
            
            num = form.cleaned_data['telefono']
            cod = form.cleaned_data['codigo_pais']
            cliente.telefono = f"{cod}{num}"
            
            cliente.save()

            for item in carrito.obtener_items():
                p = Producto.objects.get(id=item['producto_id'])
                if p.stock < item['cantidad']:
                    messages.error(request, f"Sin stock de {p.nombre}.")
                    return redirect('core:ver_carrito')

            pedido = Pedido.objects.filter(cliente=cliente, estado='Pendiente').first()
            if pedido:
                pedido.fecha = timezone.now()
                pedido.total = carrito.obtener_total_precio()
                pedido.save()
                pedido.detalles.all().delete()
            else:
                pedido = Pedido.objects.create(cliente=cliente, total=carrito.obtener_total_precio(), estado='Pendiente')

            for item in carrito.obtener_items():
                p = get_object_or_404(Producto, id=item['producto_id'])
                DetallePedido.objects.create(pedido=pedido, producto=p, cantidad=item['cantidad'], precio_unitario=item['precio'])
            
            return redirect('core:seleccion_envio', pedido_id=pedido.id)
    else:
        form = DatosEnvioForm(instance=cliente, user=request.user)

    return render(request, 'core/confirmar_compra.html', {'form': form, 'total': carrito.obtener_total_precio()})

# --- CHECKOUT PARA RESERVAS ---
@login_required
def checkout_reserva(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente__user=request.user)
    
    if pedido.estado != 'Reserva Disponible':
        return redirect('core:mis_pedidos')

    if request.method == 'POST':
        form = DatosEnvioForm(request.POST, instance=pedido.cliente, user=request.user)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()

            cliente = form.save(commit=False)
            cliente.rut = form.cleaned_data['rut']
            num = form.cleaned_data['telefono']
            cod = form.cleaned_data['codigo_pais']
            cliente.telefono = f"{cod}{num}"
            cliente.save()
            return redirect('core:seleccion_envio', pedido_id=pedido.id)
    else:
        form = DatosEnvioForm(instance=pedido.cliente, user=request.user)

    return render(request, 'core/confirmar_compra.html', {'form': form, 'total': pedido.total})

@login_required
def seleccion_envio(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente__user=request.user)
    
    # 1. Calculamos subtotal real sumando los items
    subtotal_productos = sum(d.precio_unitario * d.cantidad for d in pedido.detalles.all())
    COSTO_ENVIO_FIJO = 5990 
    UMBRAL_GRATIS = 25000
    aplica_gratis = subtotal_productos > UMBRAL_GRATIS

    if request.method == 'POST':
        tipo = request.POST.get('opcion_envio') 

        if tipo == 'despacho':
            pedido.tipo_entrega = 'Despacho'
            if not aplica_gratis:
                pedido.total = subtotal_productos + COSTO_ENVIO_FIJO
            else:
                pedido.total = subtotal_productos
        
        elif tipo == 'retiro':
            pedido.tipo_entrega = 'Retiro'
            pedido.total = subtotal_productos

        pedido.save()
        return redirect('core:seleccion_pago', pedido_id=pedido.id)

    # Pasamos las variables con el nombre correcto al template
    context = {
        'pedido': pedido,
        'subtotal': subtotal_productos,
        'costo_envio': COSTO_ENVIO_FIJO,
        'aplica_gratis': aplica_gratis
    }
    return render(request, 'core/seleccion_envio.html', context)

def seleccion_pago(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'core/seleccion_pago.html', {'pedido': pedido})

def iniciar_pago_transferencia(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.estado = 'Pendiente Pago (Transferencia)'
    pedido.save()
    try:
        grupo = Group.objects.get(name='Atencion al cliente')
        if not Notificacion.objects.filter(pedido=pedido, mensaje__contains="TRANSFERENCIA").exists():
            Notificacion.objects.create(destinatario_grupo=grupo, pedido=pedido, mensaje=f"TRANSFERENCIA: {pedido.cliente.nombre} seleccionó transf.", estado='PENDIENTE')
    except: pass
    
    Carrito(request).limpiar()
    return render(request, 'core/transferencia_instrucciones.html', {'pedido': pedido})

def iniciar_pago_webpay(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
    buy_order = f"P-{pedido.id}-{int(time.time())}"
    session_id = f"S-{request.user.id}-{int(time.time())}"
    return_url = request.build_absolute_uri('/webpay/retorno/') 
    response = tx.create(buy_order, session_id, int(pedido.total), return_url)
    return redirect(response['url'] + '?token_ws=' + response['token'])

def confirmar_pago_webpay(request):
    token = request.GET.get('token_ws') or request.POST.get('token_ws')
    if not token: return redirect('core:home')
    try:
        tx = Transaction(WebpayOptions(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY, IntegrationType.TEST))
        response = tx.commit(token)
        if response['response_code'] == 0:
            pedido_id = response['buy_order'].split('-')[1]
            pedido = Pedido.objects.get(id=pedido_id)
            pedido.estado = 'Pagado (WebPay)'
            pedido.save()
            
            # Si NO es reserva, descontamos stock. Si ES reserva, no hacemos nada (stock 0)
            if not pedido.es_reserva:
                for d in pedido.detalles.all():
                    d.producto.stock -= d.cantidad
                    d.producto.save()
            
            Carrito(request).limpiar()
            return render(request, 'core/exito.html', {'pedido_id': pedido.id})
        else:
            messages.error(request, "Pago rechazado.")
            return redirect('core:home')
    except:
        messages.error(request, "Error técnico.")
        return redirect('core:home')