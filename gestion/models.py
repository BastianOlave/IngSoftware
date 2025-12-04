from django.db import models
from django.contrib.auth.models import User, Group
import os

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2) # Usamos Decimal para dinero
    stock = models.IntegerField(default=0)
    categoria = models.CharField(max_length=50, blank=True)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    # Usamos el User de Django para la autenticación
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) 
    
    # --- NUEVO CAMPO RUT ---
    rut = models.CharField(max_length=12, blank=True, null=True, unique=True, verbose_name="RUT")
    
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En Preparacion', 'En Preparación'),
        ('En Espera Faltante', 'En espera por faltante'), 
        ('Despachado', 'Despachado'),
        ('Entregado', 'Entregado'),
        ('Cancelado', 'Cancelado'),
        ('Reserva Pendiente', 'Reserva Solicitada a Soporte'),
        ('Reserva En Camino', 'Producto Solicitado al Proveedor'),
        ('Reserva Disponible', 'Disponible para Pago'),
    ]

    TIPO_ENTREGA_CHOICES = [
        ('Despacho', 'Despacho a Domicilio'),
        ('Retiro', 'Retiro en Tienda'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='Pendiente')
    codigo_seguimiento = models.CharField(max_length=50, blank=True, null=True)
    tipo_entrega = models.CharField(max_length=20, choices=TIPO_ENTREGA_CHOICES, default='Despacho')

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente.nombre if self.cliente else 'Invitado'}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT) # Evita borrar producto si está en un pedido
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (Pedido #{self.pedido.id})"

class Notificacion(models.Model):
    # Definimos los estados posibles
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Contacto'),
        ('ESPERA', 'Esperando Respuesta del Cliente'),
        ('LISTO', 'Gestionado / Resuelto'),
        ('CANCELADO', 'Pedido Anulado')
    ]

    destinatario_grupo = models.ForeignKey(Group, on_delete=models.CASCADE)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Reemplazamos el booleano 'leido' por este campo de estado
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    pedido = models.ForeignKey(Pedido, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.estado} - {self.mensaje[:30]}"