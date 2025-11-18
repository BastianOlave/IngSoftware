from django.contrib import admin
from .models import Producto, Cliente, Pedido, DetallePedido, Notificacion

# Queremos ver los detalles del pedido DENTRO del pedido en el admin
class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1 # Cuántos formularios vacíos mostrar

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'fecha')
    inlines = [DetallePedidoInline] # Añade los detalles al admin del pedido

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock', 'categoria')
    search_fields = ('nombre', 'categoria')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'email', 'telefono')
    search_fields = ('nombre', 'apellido', 'email')

# Registra el modelo de Notificación también
admin.site.register(Notificacion)