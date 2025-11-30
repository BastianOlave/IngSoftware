from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
# En lugar de usar el decorador de Django, usamos el nuestro
# from django.contrib.auth.decorators import user_passes_test 
from core.forms import CorreoSoporteForm 
from .models import Pedido, Notificacion, Producto
from .forms import CodigoSeguimientoForm

# --- DECORADOR DE SEGURIDAD PERSONALIZADO ---
def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        # 1. Si no está logueado, al Login
        if not request.user.is_authenticated:
            # CORRECCIÓN AQUÍ: Usamos 'core:login' en vez de 'login'
            return redirect('core:login')
        
        # 2. Si está logueado pero NO es staff (Cliente normal), al Home
        if not request.user.is_staff:
            messages.error(request, "No tienes permisos para acceder a esa sección.")
            return redirect('core:home')
            
        # 3. Si es staff, pasa
        return view_func(request, *args, **kwargs)
    return wrapper

# ---------------------------------------------------------
# VISTAS PARA EL ENCARGADO DE LOGÍSTICA
# ---------------------------------------------------------

@staff_required 
def dashboard_logistica(request):
    # Muestra pedidos activos para preparar
    pedidos_pendientes = Pedido.objects.filter(
        estado__in=['Pendiente', 'En Preparacion', 'Pagado (WebPay)']
    ).order_by('fecha')
    
    return render(request, 'gestion/dashboard_logistica.html', {'pedidos': pedidos_pendientes})

@staff_required
def preparar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if pedido.estado in ['Pendiente', 'Pagado (WebPay)']:
        pedido.estado = 'En Preparacion'
        pedido.save()
    return render(request, 'gestion/preparar_pedido.html', {'pedido': pedido})

@staff_required
def confirmar_pedido_listo(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if request.method == 'POST':
        form = CodigoSeguimientoForm(request.POST, instance=pedido)
        if form.is_valid():
            # 1. Guardar código (se hace automático con form.save commit=False)
            pedido_actualizado = form.save(commit=False)
            
            # 2. Cambiar estado
            pedido_actualizado.estado = 'Despachado (WebPay)'
            pedido_actualizado.save()
            
            # 3. Enviar Correo al Cliente
            try:
                codigo = pedido_actualizado.codigo_seguimiento
                send_mail(
                    subject=f"¡Tu Pedido #{pedido.id} ha sido despachado! 🚚",
                    message=f"Hola {pedido.cliente.nombre},\n\nTu pedido ya va en camino.\n\nCódigo de Seguimiento: {codigo}\n\nPuedes revisar el estado en la sección 'Mis Pedidos' de nuestra web.\n\n¡Gracias por preferirnos!",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[pedido.cliente.email],
                    fail_silently=False,
                )
                messages.success(request, f"Pedido #{pedido.id} despachado y cliente notificado.")
            except Exception as e:
                messages.warning(request, f"Pedido despachado, pero falló el envío del correo: {e}")

            return redirect('dashboard_logistica')
    else:
        form = CodigoSeguimientoForm(instance=pedido)

    return render(request, 'gestion/ingresar_seguimiento.html', {'form': form, 'pedido': pedido})

@staff_required
def reportar_faltante(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.estado = 'En Espera Faltante'
    pedido.save()
    try:
        grupo_atencion = Group.objects.get(name='Atencion al cliente')
        Notificacion.objects.create(
            destinatario_grupo=grupo_atencion,
            pedido=pedido,
            mensaje=f"ALERTA: Faltante de stock en el Pedido #{pedido.id} ({pedido.cliente}). Revisar urgente."
        )
        messages.warning(request, f"Se ha notificado el faltante a Atención al Cliente.")
    except Group.DoesNotExist:
        messages.error(request, "Error: No existe el grupo 'Atencion al cliente'.")
    return redirect('dashboard_logistica')

@staff_required
def historial_despachos(request):
    pedidos_completados = Pedido.objects.filter(
        Q(estado__startswith='Despachado') | Q(estado__startswith='Anulado')
    ).order_by('-fecha')
    return render(request, 'gestion/historial_despachos.html', {'pedidos': pedidos_completados})

# ---------------------------------------------------------
# VISTAS PARA ATENCIÓN AL CLIENTE
# ---------------------------------------------------------

@staff_required
def dashboard_atencion(request):
    try:
        grupo_atencion = Group.objects.get(name='Atencion al cliente')
        notificaciones = Notificacion.objects.filter(
            destinatario_grupo=grupo_atencion
        ).exclude(estado__in=['LISTO', 'CANCELADO']).order_by('-fecha')
    except Group.DoesNotExist:
        notificaciones = []
    return render(request, 'gestion/dashboard_atencion.html', {'notificaciones': notificaciones})

@staff_required
def redactar_correo(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    if request.method == 'POST':
        form = CorreoSoporteForm(request.POST)
        if form.is_valid():
            mensaje = form.cleaned_data['mensaje']
            asunto = form.cleaned_data['asunto']
            
            try:
                # Envía el correo (se verá en la terminal de VS Code)
                send_mail(
                    subject=asunto,
                    message=mensaje,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[pedido.cliente.email],
                    fail_silently=False,
                )
                messages.success(request, f"Mensaje enviado correctamente a {pedido.cliente.email}.")
                
                # Cambiamos el estado de la notificación
                notif.estado = 'ESPERA'
                notif.save()
                
            except Exception as e:
                messages.error(request, "Hubo un error técnico al enviar el correo.")
                print(e)

            return redirect('dashboard_atencion')
    else:
        # AQUÍ ESTÁ EL MENSAJE PREDEFINIDO COMPLETO
        texto_inicial = (
            f"Estimado/a {pedido.cliente.nombre} {pedido.cliente.apellido},\n\n"
            f"Nos comunicamos con usted respecto a su Pedido #{pedido.id}.\n\n"
            "Lamentablemente, el equipo de logística ha detectado un quiebre de stock en uno de los productos solicitados al momento de preparar su despacho.\n\n"
            "Para solucionar esto a la brevedad, le ofrecemos las siguientes opciones:\n"
            "1. Reemplazar el producto faltante por otro de características similares.\n"
            "2. Gestionar la devolución del dinero correspondiente a ese producto.\n"
            "3. Anular la compra completa y gestionar el reembolso total.\n\n"
            "Quedamos atentos a su respuesta para proceder según su preferencia.\n\n"
            "Atentamente,\n"
            "Equipo de Atención al Cliente - Vive Sano"
        )
        
        initial_data = {
            'asunto': f"IMPORTANTE: Información sobre su Pedido #{pedido.id} - Vive Sano",
            'mensaje': texto_inicial
        }
        form = CorreoSoporteForm(initial=initial_data)

    return render(request, 'gestion/redactar_correo.html', {'form': form, 'notif': notif})

@staff_required
def registrar_respuesta(request, notificacion_id):
    messages.info(request, "Se ha registrado la respuesta del cliente.")
    return redirect('dashboard_atencion')

@staff_required
def marcar_gestionado(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    # Devolver a logística
    pedido.estado = 'En Preparacion'
    pedido.save()
    
    notif.estado = 'LISTO'
    notif.save()
    
    messages.success(request, f"Incidencia resuelta. Pedido devuelto a Logística.")
    return redirect('dashboard_atencion')

@staff_required
def anular_pedido(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    # Devolver Stock
    for detalle in pedido.detalles.all():
        producto = detalle.producto
        producto.stock += detalle.cantidad
        producto.save()
        
    pedido.estado = 'Anulado / Reembolsado'
    pedido.save()
    
    notif.estado = 'CANCELADO'
    notif.save()
    
    try:
        send_mail(
            subject=f"Pedido #{pedido.id} Cancelado",
            message="Su pedido ha sido anulado.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[pedido.cliente.email],
            fail_silently=False,
        )
    except:
        pass
    
    messages.warning(request, f"Pedido #{pedido.id} anulado.")
    return redirect('dashboard_atencion')

@staff_required
def marcar_leido(request, notificacion_id):
    return marcar_gestionado(request, notificacion_id)