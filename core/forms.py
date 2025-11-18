from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from gestion.models import Cliente
# -------------------------------------------------------
class DatosEnvioForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['direccion', 'telefono']
        widgets = {
            'direccion': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: Av. Siempreviva 742, Concepción'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: +56 9 1234 5678'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Forzamos a que sean obligatorios en este formulario
        self.fields['direccion'].required = True
        self.fields['telefono'].required = True

# -------------------------------------------------------
class RegistroClienteForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'placeholder': 'Tu nombre real'}))
    last_name = forms.CharField(label="Apellido", widget=forms.TextInput(attrs={'placeholder': 'Tu apellido'}))
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'placeholder': 'ejemplo@correo.com'}))
    
    telefono = forms.CharField(label="Teléfono", widget=forms.TextInput(attrs={'placeholder': '+56 9 ...'}))
    direccion = forms.CharField(label="Dirección", widget=forms.TextInput(attrs={'placeholder': 'Calle y número'}))
    comuna = forms.CharField(label="Comuna", widget=forms.TextInput(attrs={'placeholder': 'Ej: Providencia'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'telefono', 'direccion', 'comuna']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            direccion_completa = f"{self.cleaned_data['direccion']}, {self.cleaned_data['comuna']}"
            
            Cliente.objects.create(
                user=user,
                nombre=user.first_name,
                apellido=user.last_name,
                email=user.email,
                telefono=self.cleaned_data['telefono'],
                direccion=direccion_completa
            )
            
        return user