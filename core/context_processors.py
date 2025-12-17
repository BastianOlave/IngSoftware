from django.db.models import Q
from gestion.models import Pedido, Notificacion
from django.contrib.auth.models import Group

def contadores_globales(request):
    data = {
        'cant_logistica': 0,
        'cant_atencion': 0
    }


    if request.user.is_authenticated and request.user.is_staff:
        
        if request.user.groups.filter(name='Logistica').exists() or request.user.is_superuser:
            
            data['cant_logistica'] = Pedido.objects.filter(
                Q(estado__startswith='Pagado') | 
                Q(estado__startswith='En Preparacion') |
                Q(estado='En Espera Faltante')
            ).count()


        if request.user.groups.filter(name='Atencion al cliente').exists() or request.user.is_superuser:
            try:
                grupo_atencion = Group.objects.get(name='Atencion al cliente')
                data['cant_atencion'] = Notificacion.objects.filter(
                    destinatario_grupo=grupo_atencion
                ).exclude(estado__in=['LISTO', 'CANCELADO']).count()
            except Group.DoesNotExist:
                pass

    return data