from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.decorators import user_passes_test
from core.forms import CorreoSoporteForm 
from .models import Pedido, Notificacion, Producto

# FUNCIÓN DE SEGURIDAD: Solo deja pasar si es Staff
def es_staff(user):
    return user.is_authenticated and user.is_staff

# ---------------------------------------------------------
# VISTAS PARA EL ENCARGADO DE LOGÍSTICA (PROTEGIDAS)
# ---------------------------------------------------------

@user_passes_test(es_staff)
def dashboard_logistica(request):
    # Muestra pedidos activos: Pendientes, En Preparación y Pagados
    pedidos_pendientes = Pedido.objects.filter(
        estado__in=['Pendiente', 'En Preparacion', 'Pagado (WebPay)']
    ).order_by('fecha')
    
    return render(request, 'gestion/dashboard_logistica.html', {'pedidos': pedidos_pendientes})

@user_passes_test(es_staff)
def preparar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if pedido.estado in ['Pendiente', 'Pagado (WebPay)']:
        pedido.estado = 'En Preparacion'
        pedido.save()
        
    return render(request, 'gestion/preparar_pedido.html', {'pedido': pedido})

@user_passes_test(es_staff)
def confirmar_pedido_listo(request, pedido_id):
    # ACCIÓN A: Pedido Completo
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Marcamos como Despachado (WebPay) para mantener la trazabilidad visual
    estado_final = 'Despachado (WebPay)'
    
    # NOTA: No descontamos stock aquí porque ya lo hizo WebPay al confirmar el pago.
    # Si fuera un flujo manual (transferencia), aquí se descontaría.
    
    pedido.estado = estado_final
    pedido.save()
    
    messages.success(request, f"Pedido #{pedido.id} marcado como {estado_final}.")
    return redirect('dashboard_logistica')

@user_passes_test(es_staff)
def reportar_faltante(request, pedido_id):
    # ACCIÓN B: Problema de stock -> A Atención al Cliente
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

@user_passes_test(es_staff)
def historial_despachos(request):
    # Filtro avanzado: Busca todo lo que empiece con Despachado O Anulado
    pedidos_completados = Pedido.objects.filter(
        Q(estado__startswith='Despachado') | Q(estado__startswith='Anulado')
    ).order_by('-fecha')
    
    return render(request, 'gestion/historial_despachos.html', {'pedidos': pedidos_completados})

# ---------------------------------------------------------
# VISTAS PARA ATENCIÓN AL CLIENTE (CRM) - PROTEGIDAS
# ---------------------------------------------------------

@user_passes_test(es_staff)
def dashboard_atencion(request):
    try:
        grupo_atencion = Group.objects.get(name='Atencion al cliente')
        notificaciones = Notificacion.objects.filter(
            destinatario_grupo=grupo_atencion
        ).exclude(estado__in=['LISTO', 'CANCELADO']).order_by('-fecha')
    except Group.DoesNotExist:
        notificaciones = []
        
    return render(request, 'gestion/dashboard_atencion.html', {'notificaciones': notificaciones})

@user_passes_test(es_staff)
def redactar_correo(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    if request.method == 'POST':
        form = CorreoSoporteForm(request.POST)
        if form.is_valid():
            mensaje = form.cleaned_data['mensaje']
            asunto = form.cleaned_data['asunto']
            
            try:
                send_mail(
                    subject=asunto,
                    message=mensaje,
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
            f"Estimado/a {pedido.cliente.nombre},\n\n"
            f"Nos comunicamos respecto a su Pedido #{pedido.id}. "
            "Lamentablemente tenemos un quiebre de stock.\n\n"
            "Opciones:\n1. Cambio de producto.\n2. Reembolso.\n\n"
            "Quedamos atentos."
        )
        initial_data = {
            'asunto': f"URGENTE: Pedido #{pedido.id} - Vive Sano",
            'mensaje': texto_inicial
        }
        form = CorreoSoporteForm(initial=initial_data)

    return render(request, 'gestion/redactar_correo.html', {'form': form, 'notif': notif})

@user_passes_test(es_staff)
def registrar_respuesta(request, notificacion_id):
    messages.info(request, "Se ha registrado la respuesta del cliente.")
    return redirect('dashboard_atencion')

@user_passes_test(es_staff)
def marcar_gestionado(request, notificacion_id):
    # CASO 1: Cliente acepta solución (Resuelto) -> Vuelve a Logística
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    pedido = notif.pedido
    
    pedido.estado = 'En Preparacion'
    pedido.save()
    
    notif.estado = 'LISTO'
    notif.save()
    
    messages.success(request, f"Incidencia resuelta. Pedido devuelto a Logística.")
    return redirect('dashboard_atencion')

@user_passes_test(es_staff)
def anular_pedido(request, notificacion_id):
    # CASO 2: Cliente pide reembolso (Cancelado)
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
    
    # Correo automático de cancelación
    try:
        send_mail(
            subject=f"Pedido #{pedido.id} Cancelado - Vive Sano",
            message=f"Estimado/a,\n\nSu Pedido #{pedido.id} ha sido cancelado y su reembolso gestionado.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[pedido.cliente.email],
            fail_silently=False,
        )
    except:
        pass
    
    messages.warning(request, f"Pedido #{pedido.id} anulado. Stock restaurado.")
    return redirect('dashboard_atencion')

@user_passes_test(es_staff)
def marcar_leido(request, notificacion_id):
    return marcar_gestionado(request, notificacion_id)