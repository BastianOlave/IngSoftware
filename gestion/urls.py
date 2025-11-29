from django.urls import path
from . import views

urlpatterns = [
    # Rutas de Logística
    path('logistica/', views.dashboard_logistica, name='dashboard_logistica'),
    path('logistica/preparar/<int:pedido_id>/', views.preparar_pedido, name='preparar_pedido'),
    path('logistica/confirmar/<int:pedido_id>/', views.confirmar_pedido_listo, name='confirmar_pedido'),
    path('logistica/reportar/<int:pedido_id>/', views.reportar_faltante, name='reportar_faltante'),
    path('logistica/historial/', views.historial_despachos, name='historial_despachos'),

    # Rutas de Atención al Cliente
    path('atencion/', views.dashboard_atencion, name='dashboard_atencion'),
    path('atencion/leido/<int:notificacion_id>/', views.marcar_leido, name='marcar_leido'),
]