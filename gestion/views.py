from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group
from django.contrib import messages
from .models import Pedido, Notificacion, Producto


def dashboard_logistica(request):
    # Muestra los pedidos que necesitan atención (Pendientes o En Preparación)
    pedidos_pendientes = Pedido.objects.filter(estado__in=['Pendiente', 'En Preparacion']).order_by('fecha')
    return render(request, 'gestion/dashboard_logistica.html', {'pedidos': pedidos_pendientes})

def preparar_pedido(request, pedido_id):
    # Muestra el detalle de un pedido específico para prepararlo
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Si es la primera vez que entra, cambiamos estado a "En Preparación"
    if pedido.estado == 'Pendiente':
        pedido.estado = 'En Preparacion'
        pedido.save()
        
    return render(request, 'gestion/preparar_pedido.html', {'pedido': pedido})

def confirmar_pedido_listo(request, pedido_id):
    # ACCIÓN A: El pedido está completo. Descontamos stock y finalizamos.
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # 1. Descontar Stock (Requisito HU003)
    for detalle in pedido.detalles.all():
        producto = detalle.producto
        producto.stock -= detalle.cantidad
        producto.save()
    
    # 2. Cambiar estado
    pedido.estado = 'Despachado'
    pedido.save()
    
    messages.success(request, f"Pedido #{pedido.id} despachado y stock actualizado.")
    return redirect('dashboard_logistica')

def reportar_faltante(request, pedido_id):
    # ACCIÓN B: Falta un producto. Notificar a Atención al Cliente. (HU004/HU005)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # 1. Cambiar estado del pedido
    pedido.estado = 'En Espera Faltante'
    pedido.save()
    
    # 2. Crear Notificación para Atención al Cliente (HU005)
    # Buscamos el grupo destinatario
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

# ---------------------------------------------------------
# VISTAS PARA ATENCIÓN AL CLIENTE (HU005)
# ---------------------------------------------------------

def dashboard_atencion(request):
    # Muestra las notificaciones dirigidas a este rol
    try:
        grupo_atencion = Group.objects.get(name='Atencion al cliente')
        notificaciones = Notificacion.objects.filter(destinatario_grupo=grupo_atencion, leido=False).order_by('-fecha')
    except Group.DoesNotExist:
        notificaciones = []
        
    return render(request, 'gestion/dashboard_atencion.html', {'notificaciones': notificaciones})

def marcar_leido(request, notificacion_id):
    notif = get_object_or_404(Notificacion, id=notificacion_id)
    notif.leido = True
    notif.save()
    return redirect('dashboard_atencion')

def historial_despachos(request):
    # Filtramos solo los pedidos que ya fueron 'Despachados' o 'Pagados'
    # Ajusta los estados según lo que use tu sistema finalmente
    pedidos_completados = Pedido.objects.filter(estado__in=['Despachado', 'Pagado (WebPay)']).order_by('-fecha')
    
    return render(request, 'gestion/historial_despachos.html', {'pedidos': pedidos_completados})