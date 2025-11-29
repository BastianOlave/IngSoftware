from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from gestion.models import Cliente

# -------------------------------------------------------
# FORMULARIO 1: Checkout Completo
# -------------------------------------------------------
class DatosEnvioForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellido", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
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
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_codigo_pais'})
    )
    
    telefono = forms.CharField(
        label="Teléfono", 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '12345678',
            'type': 'tel',       
            'maxlength': '8',    
            'id': 'input-telefono' 
        }),
        help_text="Ingresa los 8 dígitos restantes."
    )

    codigo_postal = forms.CharField(
        label="Código Postal",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 4030000'}),
        help_text='<a href="https://www.correos.cl/codigo-postal" target="_blank" class="text-decoration-none">🔍 Buscar mi Código en Correos.cl</a>'
    )

    class Meta:
        model = Cliente
        fields = ['direccion', 'comuna', 'codigo_postal']
        widgets = {
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle y número'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Concepción'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
        
        if self.instance.pk and self.instance.telefono:
            tel_guardado = self.instance.telefono
            for codigo, label in self.PAIS_CHOICES:
                if tel_guardado.startswith(codigo):
                    self.fields['codigo_pais'].initial = codigo
                    self.fields['telefono'].initial = tel_guardado[len(codigo):]
                    break
        
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['direccion'].required = True
        self.fields['comuna'].required = True
        self.fields['telefono'].required = True
        self.fields['codigo_postal'].required = True

# -------------------------------------------------------
# FORMULARIO 2: Registro Rápido
# -------------------------------------------------------
class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'placeholder': 'ejemplo@correo.cl'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {'username': 'Nombre de usuario'}
        help_texts = {'username': None}

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Cliente.objects.create(user=user, email=user.email)
        return user

# -------------------------------------------------------
# FORMULARIO 3: Soporte / Atención al Cliente
# -------------------------------------------------------
class CorreoSoporteForm(forms.Form):
    asunto = forms.CharField(
        label="Asunto", 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    mensaje = forms.CharField(
        label="Mensaje para el Cliente", 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'style': 'resize: none;'})
    )

# -------------------------------------------------------
# FORMULARIO 4: Mi Perfil (ACTUALIZADO)
# -------------------------------------------------------
class PerfilUsuarioForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellido", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    # Selector de País (Mismo ID que checkout para usar el script de banderas)
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
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_codigo_pais'})
    )

    # Teléfono con límite (Mismo ID que checkout para usar el script de validación)
    telefono = forms.CharField(
        label="Teléfono", 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '12345678',
            'type': 'tel',       
            'maxlength': '8',    
            'id': 'input-telefono'
        }),
        help_text="Ingresa los 8 dígitos restantes."
    )

    direccion = forms.CharField(label="Dirección", widget=forms.TextInput(attrs={'class': 'form-control'}))
    comuna = forms.CharField(label="Comuna", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # Código Postal con enlace
    codigo_postal = forms.CharField(
        label="Código Postal",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 4030000'}),
        help_text='<a href="https://www.correos.cl/codigo-postal" target="_blank" class="text-decoration-none">🔍 Buscar mi Código en Correos.cl</a>'
    )

    class Meta:
        model = Cliente
        fields = ['direccion', 'comuna', 'codigo_postal']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
        
        # Separar teléfono si ya existe
        if self.instance.pk and self.instance.telefono:
            tel_guardado = self.instance.telefono
            for codigo, label in self.PAIS_CHOICES:
                if tel_guardado.startswith(codigo):
                    self.fields['codigo_pais'].initial = codigo
                    self.fields['telefono'].initial = tel_guardado[len(codigo):]
                    break