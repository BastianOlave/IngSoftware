from decimal import Decimal
from django.conf import settings
from gestion.models import Producto

class Carrito:
    def __init__(self, request):
        self.session = request.session
        carrito = self.session.get("carrito")
        if not carrito:
            carrito = self.session["carrito"] = {}
        self.carrito = carrito

    def agregar(self, producto, cantidad=1):
        producto_id = str(producto.id)
        if producto_id not in self.carrito:
            self.carrito[producto_id] = {
                'producto_id': producto.id,
                'nombre': producto.nombre,
                'precio': str(producto.precio),
                'cantidad': 0,
                'imagen': '' # Placeholder por si agregamos imágenes luego
            }
        self.carrito[producto_id]['cantidad'] += int(cantidad)
        self.guardar()

    def guardar(self):
        self.session.modified = True

    def eliminar(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.guardar()

    def limpiar(self):
        self.session["carrito"] = {}
        self.guardar()
    
    def obtener_total_precio(self):
        return sum(Decimal(item['precio']) * item['cantidad'] for item in self.carrito.values())
    
    def __len__(self):
        return sum(item['cantidad'] for item in self.carrito.values())
        
    def obtener_items(self):
        return self.carrito.values()
    
    def actualizar(self, producto, cantidad):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            self.carrito[producto_id]['cantidad'] = cantidad
            self.guardar()