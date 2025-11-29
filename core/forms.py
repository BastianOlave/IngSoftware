from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from gestion.models import Cliente

# -------------------------------------------------------
# FORMULARIO 1: Checkout Completo (Datos Personales + Envío)
# -------------------------------------------------------
class DatosEnvioForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellido", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # 1. CAMBIO DE BANDERAS
    PAIS_CHOICES = [
        ('+569', 'Chile (+56 9)'),
        ('+54',  'Argentina (+54)'),
        ('+51',  'Perú (+51)'),
        ('+57',  'Colombia (+57)'),
    ]
    
    codigo_pais = forms.ChoiceField(
        choices=PAIS_CHOICES, 
        label="País",
        initial='+569',
        widget=forms.Select(attrs={
            'class': 'form-select', 
            'id': 'id_codigo_pais' # Aseguramos el ID para el JavaScript
        })
    )
    
    telefono = forms.CharField(
        label="Teléfono", 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678'}),
        help_text="Ingresa los dígitos restantes."
    )

    class Meta:
        model = Cliente
        fields = ['direccion', 'comuna']
        widgets = {
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle y número'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Concepción'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # A) PRE-LLENAR NOMBRE Y APELLIDO DESDE EL USUARIO
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
        
        # B) PRE-LLENAR TELÉFONO (LÓGICA DE PERSISTENCIA)
        # Si el cliente ya existe (self.instance.pk) y tiene un teléfono guardado...
        if self.instance.pk and self.instance.telefono:
            tel_guardado = self.instance.telefono
            
            # Revisamos con qué código empieza para separar los campos
            for codigo, label in self.PAIS_CHOICES:
                if tel_guardado.startswith(codigo):
                    # Ponemos el código en el selector
                    self.fields['codigo_pais'].initial = codigo
                    # Ponemos el resto del número en el campo de texto
                    # len(codigo) calcula el largo (ej: +569 son 4 letras)
                    self.fields['telefono'].initial = tel_guardado[len(codigo):]
                    break
        
        # Validaciones obligatorias
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['direccion'].required = True
        self.fields['comuna'].required = True
        self.fields['telefono'].required = True

# -------------------------------------------------------
# FORMULARIO 2: Registro Rápido (Solo Email)
# -------------------------------------------------------
class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'placeholder': 'ejemplo@correo.cl'}))

    class Meta:
        model = User
        fields = ['username', 'email'] # Quitamos nombre, apellido y teléfono
        labels = {'username': 'Nombre de usuario'}
        help_texts = {'username': None}

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Creamos el cliente vacío, se rellenará en el checkout
            Cliente.objects.create(user=user, email=user.email)
        return user