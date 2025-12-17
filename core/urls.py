from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle'),
    
    # Carrito
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_producto, name='agregar'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_carrito, name='actualizar'),

    # Usuario
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('perfil/', views.perfil_usuario, name='perfil'),
    
    # Checkout Normal
    path('checkout/', views.checkout, name='checkout'),
    
    # Checkout de Reserva
    path('checkout/reserva/<int:pedido_id>/', views.checkout_reserva, name='checkout_reserva'),

    path('checkout/envio/<int:pedido_id>/', views.seleccion_envio, name='seleccion_envio'),
    path('pago/<int:pedido_id>/', views.seleccion_pago, name='seleccion_pago'),
    path('pago/transferencia/<int:pedido_id>/', views.iniciar_pago_transferencia, name='iniciar_transferencia'),
    path('webpay/iniciar/<int:pedido_id>/', views.iniciar_pago_webpay, name='iniciar_webpay'),
    path('webpay/retorno/', views.confirmar_pago_webpay, name='webpay_retorno'),

    # Mis Pedidos
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('mis-pedidos/detalle/<int:pedido_id>/', views.detalle_pedido_cliente, name='detalle_pedido_cliente'),

    # Reservar
    path('reservar/<int:producto_id>/', views.reservar_producto, name='reservar_producto'),
]