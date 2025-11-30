from django import forms
from .models import Pedido

class CodigoSeguimientoForm(forms.ModelForm):
    codigo_seguimiento = forms.CharField(
        label="Código de Seguimiento (Courier)",
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': 'Ej: 123456789012',
            'autofocus': 'autofocus'
        }),
        help_text="Ingresa el código proporcionado por el courier (Máx 12 caracteres)."
    )

    class Meta:
        model = Pedido
        fields = ['codigo_seguimiento']