from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from gestion.models import Cliente
from itertools import cycle

# -------------------------------------------------------
# LÓGICA DE VALIDACIÓN RUT (Módulo 11)
# -------------------------------------------------------
def validar_rut_chileno(rut):
    # 1. Limpiamos puntos y guiones y pasamos a mayúsculas
    rut_limpio = rut.replace('.', '').replace('-', '').upper()
    
    # Validaciones básicas de largo
    if not rut_limpio or len(rut_limpio) < 8:
        return False
        
    cuerpo = rut_limpio[:-1]
    dv_ingresado = rut_limpio[-1]
    
    # El cuerpo debe ser numérico
    if not cuerpo.isdigit():
        return False
        
    # Algoritmo matemático Módulo 11
    try:
        # Invertimos el cuerpo para multiplicar de derecha a izquierda
        reverso = map(int, reversed(str(cuerpo)))
        factors = cycle(range(2, 8)) # Secuencia 2, 3, 4, 5, 6, 7, 2, 3...
        s = sum(d * f for d, f in zip(reverso, factors))
        res = (-s) % 11
        
        if res == 10:
            dv_esperado = 'K'
        elif res == 11:
            dv_esperado = '0'
        else:
            dv_esperado = str(res)
            
        return dv_ingresado == dv_esperado
    except ValueError:
        return False

# -------------------------------------------------------
# FORMULARIO 1: Checkout Completo
# -------------------------------------------------------
class DatosEnvioForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellido", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # --- CAMPO RUT CON LÍMITE DE 12 CARACTERES ---
    rut = forms.CharField(
        label='RUT', 
        required=True, 
        widget=forms.TextInput(attrs={
            'placeholder': '12.345.678-9',
            'class': 'form-control rut-input', 
            'maxlength': '12' # <--- ESTO EVITA QUE ESCRIBAN MÁS DE LA CUENTA
        }),
        help_text="Sin puntos ni guión (se formateará automático)."
    )
    
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
        fields = ['direccion', 'comuna', 'codigo_postal', 'rut']
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
            # Cargar RUT si existe
            try:
                if hasattr(user, 'cliente'):
                    self.fields['rut'].initial = user.cliente.rut
            except:
                pass
        
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

    # VALIDACIÓN DEL RUT
    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not validar_rut_chileno(rut):
            raise forms.ValidationError("El RUT ingresado no es válido (Revisa el dígito verificador).")
        return rut

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
    
    # --- CAMPO RUT CON LÍMITE DE 12 CARACTERES ---
    rut = forms.CharField(
        label='RUT', 
        required=True, 
        widget=forms.TextInput(attrs={
            'class': 'form-control rut-input', 
            'placeholder': '12.345.678-9',
            'maxlength': '12' # <--- LÍMITE APLICADO
        })
    )
    
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

    direccion = forms.CharField(label="Dirección", widget=forms.TextInput(attrs={'class': 'form-control'}))
    comuna = forms.CharField(label="Comuna", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    codigo_postal = forms.CharField(
        label="Código Postal",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 4030000'}),
        help_text='<a href="https://www.correos.cl/codigo-postal" target="_blank" class="text-decoration-none">🔍 Buscar mi Código en Correos.cl</a>'
    )

    class Meta:
        model = Cliente
        fields = ['direccion', 'comuna', 'codigo_postal', 'rut']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
        
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

    # VALIDACIÓN DEL RUT EN PERFIL
    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        
        # Validamos formato matemático
        if not validar_rut_chileno(rut):
            raise forms.ValidationError("RUT inválido.")
            
        # Validamos que no pertenezca a OTRO usuario (unicidad)
        existe_otro = Cliente.objects.filter(rut=rut).exclude(user=self.user).exists()
        if existe_otro:
            raise forms.ValidationError("Este RUT ya está registrado en otra cuenta.")
            
        return rut