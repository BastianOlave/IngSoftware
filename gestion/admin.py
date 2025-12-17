from django.contrib import admin
from .models import Producto, Cliente, Pedido, DetallePedido, Notificacion

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1 

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'fecha')
    inlines = [DetallePedidoInline] 

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'categoria')
    search_fields = ('nombre', 'categoria')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'email', 'telefono')
    search_fields = ('nombre', 'apellido', 'email')

admin.site.register(Notificacion)