from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
# Importamos formularios
from core.forms import CorreoSoporteForm 
from .forms import CodigoSeguimientoForm
from .models import Pedido, Notificacion, Producto

def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if not request.user.is_staff:
            messages.error(request, "No tienes permisos para acceder a esa sección.")
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper

# --- LOGÍSTICA ---

@staff_required 
def dashboard_logistica(request):
    # SEGURIDAD: Eliminamos 'Pendiente' de la lista.
    pedidos_pendientes = Pedido.objects.filter(
        Q(estado__startswith='Pagado') | 
        Q(estado__startswith='En Preparacion') |
        Q(estado='En Espera Faltante')
    ).order_by('fecha')
    
    return render(request, 'gestion/dashboard_logistica.html', {'pedidos': pedidos_pendientes})

@staff_required
def preparar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # SEGURIDAD: Si intentan entrar por URL a un pedido que sigue Pendiente
    if 'Pendiente' in pedido.estado and 'Pago' not in pedido.estado:
         messages.error(request, "¡Alto ahí! Ese pedido aún no ha sido pagado.")
         return redirect('dashboard_logistica')

    # Lógica de cambio de estado
    if 'Pagado' in pedido.estado:
        if 'Transferencia' in pedido.estado:
            pedido.estado = 'En Preparacion (Transferencia)'
        else:
            pedido.estado = 'En Preparacion (WebPay)'
            
        pedido.save()
        
    return render(request, 'gestion/preparar_pedido.html', {'pedido': pedido})

@staff_required
def confirmar_pedido_listo(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # --- LOGICA AUTOMÁTICA PARA RETIRO ---
    if pedido.tipo_entrega == 'Retiro':
        pedido.codigo_seguimiento = "Retiro en Tienda"
        
        if 'Transferencia' in pedido.estado:
            pedido.estado = 'Despachado (Retiro/Transferencia)'
        else:
            pedido.estado = 'Despachado (Retiro/WebPay)'
        
        pedido.save()
        
        try:
            send_mail(
                subject=f"¡Tu Pedido #{pedido.id} está listo para retiro! 🛍️",
                message=f"Hola {pedido.cliente.nombre},\n\nTu pedido ya está listo en nuestra tienda.\n\nPuedes pasar a retirarlo en nuestro horario de atención.\n\n¡Te esperamos!",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[pedido.cliente.email],
                fail_silently=False,
            )
            messages.success(request, f"Pedido #{pedido.id} marcado como 'Listo para Retiro'.")
        except:
            messages.warning(request, "Pedido listo, pero falló el correo.")
            
        return redirect('dashboard_logistica')

    # --- LOGICA NORMAL PARA DESPACHO ---
    if request.method == 'POST':
        form = CodigoSeguimientoForm(request.POST, instance=pedido)
        if form.is_valid():
            pedido_actualizado = form.save(commit=False)
            
            if 'Transferencia' in pedido.estado:
                estado_final = 'Despachado (Transferencia)'
            else:
                estado_final = 'Despachado (WebPay)'
            
            pedido_actualizado.estado = estado_final
            pedido_actualizado.save()
            
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
                messages.warning(request, f"Pedido despachado, pero falló el envío del correo.")

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

# --- ATENCIÓN AL CLIENTE ---

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
def confirmar_transferencia(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    for detalle in pedido.detalles.all():
        producto = detalle.producto
        producto.stock -= detalle.cantidad
        producto.save()
    
    pedido.estado = 'Pagado (Transferencia)'
    pedido.save()
    
    notif.estado = 'LISTO'
    notif.save()
    
    messages.success(request, f"Pago de Pedido #{pedido.id} confirmado. Enviado a Logística.")
    return redirect('dashboard_atencion')

@staff_required
def redactar_correo(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    if request.method == 'POST':
        form = CorreoSoporteForm(request.POST)
        if form.is_valid():
            try:
                send_mail(
                    subject=form.cleaned_data['asunto'],
                    message=form.cleaned_data['mensaje'],
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[pedido.cliente.email],
                    fail_silently=False,
                )
                messages.success(request, f"Mensaje enviado a {pedido.cliente.email}.")
                notif.estado = 'ESPERA'
                notif.save()
            except Exception as e:
                messages.error(request, "Error al enviar correo.")
                print(e)
            return redirect('dashboard_atencion')
    else:
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
    
    fue_transferencia = Notificacion.objects.filter(
        pedido=pedido, 
        mensaje__contains="TRANSFERENCIA"
    ).exists()

    if fue_transferencia:
        pedido.estado = 'En Preparacion (Transferencia)'
    else:
        pedido.estado = 'En Preparacion (WebPay)'
        
    pedido.save()
    
    notif.estado = 'LISTO'
    notif.save()
    
    messages.success(request, f"Incidencia resuelta. Pedido devuelto a Logística.")
    return redirect('dashboard_atencion')

@staff_required
def anular_pedido(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    if 'Pagado' in pedido.estado or 'En Preparacion' in pedido.estado:
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