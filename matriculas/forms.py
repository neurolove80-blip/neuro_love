from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import PerfilUsuario, ProcesoPsicologico, ConsejoProceso, HistoriaClinica, Libro, Video, TemaForo, Conversacion, MensajeForo, CalendarioConfig, DiaNoHabil, Cita, ConfigTipoCita

ROL_CHOICES_PUBLICO = [
    ('profesor',  'Profesor'),
    ('psicologo', 'Psicólogo'),
]

WIDGET_INPUT  = {'class': 'form-control'}
WIDGET_SELECT = {'class': 'form-select'}
WIDGET_AREA   = {'class': 'form-control', 'rows': 4}


PALABRA_SEGURIDAD = 'sanfrancisco'

# ── REGISTRO ──────────────────────────
class RegistroForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=60, label='Nombre Completo',
        widget=forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Juan Pérez'})
    )
    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={**WIDGET_INPUT, 'placeholder': 'usuario@gmail.com'})
    )
    rol = forms.ChoiceField(
        choices=ROL_CHOICES_PUBLICO, label='Rol',
        widget=forms.Select(attrs=WIDGET_SELECT)
    )
    palabra_seguridad = forms.CharField(
        required=False,
        label='Palabra de Seguridad',
        widget=forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Ingresa la palabra de seguridad'}),
        help_text='Solo para registro de psicólogo'
    )

    class Meta:
        model  = User
        fields = ('first_name', 'email', 'username', 'password1', 'password2', 'rol', 'palabra_seguridad')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('username', 'password1', 'password2'):
            self.fields[field].widget.attrs.update(WIDGET_INPUT)

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get('rol')
        palabra = cleaned_data.get('palabra_seguridad', '').strip().lower()
        if rol == 'psicologo' and palabra != PALABRA_SEGURIDAD:
            raise ValidationError({
                'palabra_seguridad': 'Palabra de seguridad incorrecta para registro de psicólogo.'
            })
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        if commit:
            user.save()
            PerfilUsuario.objects.create(usuario=user, rol=self.cleaned_data['rol'])
        return user


# ── PROCESO ───────────────────────────
class ProcesoForm(forms.ModelForm):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )

    class Meta:
        model  = ProcesoPsicologico
        fields = ('tipo_identificacion', 'numero_identificacion', 'nombre_estudiante', 'grado', 'tipo_proceso', 'estado', 'fecha_inicio', 'fecha_fin', 'descripcion')
        labels = {
            'tipo_identificacion':   'Tipo de Identificación',
            'numero_identificacion': 'Número de Identificación',
            'nombre_estudiante':      'Nombre del Estudiante',
            'grado':                  'Grado',
            'tipo_proceso':           'Tipo de Proceso',
            'estado':                 'Estado',
            'fecha_inicio':           'Fecha de Inicio',
            'fecha_fin':             'Fecha de Fin',
            'descripcion':            'Descripción del Proceso',
        }
        widgets = {
            'tipo_identificacion':   forms.Select(attrs=WIDGET_SELECT),
            'numero_identificacion': forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': '12345678'}),
            'nombre_estudiante':     forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Pepito Pérez'}),
            'grado':                  forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': '8A'}),
            'tipo_proceso':           forms.Select(attrs=WIDGET_SELECT),
            'estado':                 forms.Select(attrs=WIDGET_SELECT),
            'fecha_inicio':           forms.DateInput(attrs={**WIDGET_INPUT, 'type': 'date'}),
            'fecha_fin':             forms.DateInput(attrs={**WIDGET_INPUT, 'type': 'date'}),
            'descripcion':            forms.Textarea(attrs=WIDGET_AREA),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        if fecha_fin and fecha_inicio:
            if fecha_fin < fecha_inicio:
                raise ValidationError({'fecha_fin': 'La fecha de fin debe ser mayor o igual a la fecha de inicio.'})


# ── CONSEJO ───────────────────────────
class ConsejoForm(forms.ModelForm):
    class Meta:
        model   = ConsejoProceso
        fields  = ('texto',)
        labels  = {'texto': 'Tu Ajuste Razonable o Recomendación'}
        widgets = {'texto': forms.Textarea(attrs={**WIDGET_AREA, 'placeholder': 'Escribe aquí tu observación o ajuste razonable...'})}


# ── LIBRO ─────────────────────────────
class LibroForm(forms.ModelForm):
    class Meta:
        model  = Libro
        fields = ('titulo', 'autor', 'categoria', 'descripcion', 'fecha_publicacion', 'archivo', 'imagen_portada', 'color_portada')
        labels = {
            'titulo':             'Título del Libro',
            'autor':              'Autor',
            'categoria':          'Categoría',
            'descripcion':        'Descripción',
            'fecha_publicacion':  'Fecha de Publicación',
            'archivo':            'Archivo PDF (opcional)',
            'imagen_portada':     'Imagen de portada (opcional)',
            'color_portada':      'Color de respaldo',
        }
        widgets = {
            'titulo':            forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Los hábitos de un cerebro feliz'}),
            'autor':             forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Loretta Graziano'}),
            'categoria':         forms.Select(attrs=WIDGET_SELECT),
            'descripcion':       forms.Textarea(attrs=WIDGET_AREA),
            'fecha_publicacion': forms.DateInput(attrs={**WIDGET_INPUT, 'type': 'date'}),
            'imagen_portada':    forms.FileInput(attrs={'accept': 'image/*'}),
            'color_portada':     forms.TextInput(attrs={**WIDGET_INPUT, 'type': 'color'}),
        }


# ── TEMA FORO ─────────────────────────
class TemaForoForm(forms.ModelForm):
    class Meta:
        model  = TemaForo
        fields = ('titulo', 'categoria', 'descripcion')
        labels = {
            'titulo':      'Título del Tema',
            'categoria':   'Categoría',
            'descripcion': 'Descripción del Tema',
        }
        widgets = {
            'titulo':      forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': '¿Cuál es la mejor estrategia...?'}),
            'categoria':   forms.Select(attrs=WIDGET_SELECT),
            'descripcion': forms.Textarea(attrs={**WIDGET_AREA, 'placeholder': 'Describe tu pregunta...'}),
        }


# ── MENSAJE FORO ────────────────────
class MensajeForoForm(forms.ModelForm):
    class Meta:
        model  = MensajeForo
        fields = ('texto',)
        labels = {'texto': 'Mensaje'}
        widgets = {'texto': forms.Textarea(attrs={**WIDGET_AREA, 'placeholder': 'Escribe tu mensaje...'})}


# ── HISTORIA CLÍNICA ────────────────
class HistoriaClinicaForm(forms.ModelForm):
    class Meta:
        model  = HistoriaClinica
        fields = ('contenido',)
        labels = {'contenido': 'Nueva Entrada'}
        widgets = {'contenido': forms.Textarea(attrs={**WIDGET_AREA, 'placeholder': 'Registra la nueva entrada de la historia clínica...'})}


# ── CALENDARIO ───────────────────────
class CalendarioConfigForm(forms.ModelForm):
    class Meta:
        model  = CalendarioConfig
        fields = ('dia_inicio_semana', 'hora_inicio', 'hora_fin')
        labels = {
            'dia_inicio_semana': 'Primer día de la semana',
            'hora_inicio':       'Hora de inicio de atención',
            'hora_fin':          'Hora de fin de atención',
        }
        widgets = {
            'dia_inicio_semana': forms.Select(attrs=WIDGET_SELECT),
            'hora_inicio':       forms.TimeInput(attrs={**WIDGET_INPUT, 'type': 'time'}),
            'hora_fin':          forms.TimeInput(attrs={**WIDGET_INPUT, 'type': 'time'}),
        }


class DiaNoHabilForm(forms.ModelForm):
    class Meta:
        model  = DiaNoHabil
        fields = ('fecha', 'motivo', 'es_recurrente')
        labels = {
            'fecha':          'Fecha',
            'motivo':        'Motivo',
            'es_recurrente': 'Se repite anualmente',
        }
        widgets = {
            'fecha': forms.DateInput(attrs={**WIDGET_INPUT, 'type': 'date'}),
            'motivo': forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Ej: Festivo, Vacaciones'}),
        }


# ── VIDEO ─────────────────────────────
class VideoForm(forms.ModelForm):
    class Meta:
        model  = Video
        fields = ('titulo', 'url', 'categoria', 'descripcion')
        labels = {
            'titulo':      'Título del Video',
            'url':         'URL de YouTube',
            'categoria':   'Categoría',
            'descripcion': 'Descripción',
        }
        widgets = {
            'titulo':      forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Ej: Estrategias para el aula'}),
            'url':         forms.URLInput(attrs={**WIDGET_INPUT, 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'categoria':   forms.Select(attrs=WIDGET_SELECT),
            'descripcion': forms.Textarea(attrs=WIDGET_AREA),
        }


# ── ADMIN: CREAR USUARIO ─────────────
class AdminCrearUsuarioForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=60, label='Nombre Completo',
        widget=forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Juan Pérez'})
    )
    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={**WIDGET_INPUT, 'placeholder': 'usuario@gmail.com'})
    )
    rol = forms.ChoiceField(
        choices=PerfilUsuario.ROL_CHOICES, label='Rol',
        widget=forms.Select(attrs=WIDGET_SELECT)
    )
    is_active = forms.BooleanField(
        required=False, initial=True, label='Usuario Activo',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model  = User
        fields = ('first_name', 'email', 'username', 'password1', 'password2', 'rol', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('username', 'password1', 'password2'):
            self.fields[field].widget.attrs.update(WIDGET_INPUT)
        self.fields['is_active'].initial = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.is_active  = self.cleaned_data.get('is_active', True)
        if commit:
            user.save()
            PerfilUsuario.objects.create(usuario=user, rol=self.cleaned_data['rol'])
        return user


# ── ADMIN: EDITAR USUARIO ─────────────
class AdminEditarUsuarioForm(forms.ModelForm):
    rol = forms.ChoiceField(
        choices=PerfilUsuario.ROL_CHOICES, label='Rol',
        widget=forms.Select(attrs=WIDGET_SELECT)
    )
    nueva_password = forms.CharField(
        required=False, label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={**WIDGET_INPUT, 'placeholder': 'Dejar vacío para no cambiar'}),
    )
    confirmar_password = forms.CharField(
        required=False, label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={**WIDGET_INPUT, 'placeholder': 'Repite la nueva contraseña'}),
    )

    class Meta:
        model  = User
        fields = ('first_name', 'email', 'username', 'is_active')
        labels = {
            'first_name': 'Nombre Completo',
            'email':      'Correo Electrónico',
            'username':   'Nombre de Usuario',
            'is_active':  'Usuario Activo',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Juan Pérez'}),
            'email':      forms.EmailInput(attrs={**WIDGET_INPUT, 'placeholder': 'usuario@gmail.com'}),
            'username':   forms.TextInput(attrs=WIDGET_INPUT),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'perfil'):
            self.fields['rol'].initial = self.instance.perfil.rol

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('nueva_password')
        p2 = cleaned_data.get('confirmar_password')
        if p1 and p1 != p2:
            raise ValidationError({'confirmar_password': 'Las contraseñas no coinciden.'})
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        nueva = self.cleaned_data.get('nueva_password')
        if nueva:
            user.set_password(nueva)
            user.save()
        rol = self.cleaned_data.get('rol')
        if rol and hasattr(user, 'perfil'):
            user.perfil.rol = rol
            user.perfil.save()
        return user


class CitaForm(forms.ModelForm):
    fecha_hora = forms.DateTimeField(
        label='Fecha y Hora',
        widget=forms.DateTimeInput(attrs={**WIDGET_INPUT, 'type': 'datetime-local'}),
        required=True
    )
    tipo_cita = forms.ChoiceField(
        label='Tipo de Cita',
        required=False,
        choices=[],
        widget=forms.Select(attrs=WIDGET_SELECT)
    )
    
    class Meta:
        model  = Cita
        fields = ('estudiante', 'titulo', 'fecha_hora', 'duracion', 'observaciones', 'recordar')
        labels = {
            'estudiante':   'Estudiante (opcional)',
            'tipo_cita':    'Tipo de Cita',
            'titulo':       'Título de la Cita',
            'fecha_hora':   'Fecha y Hora',
            'duracion':     'Duración (minutos)',
            'observaciones':'Observaciones',
            'recordar':      'Recordar 1 hora antes',
        }
        widgets = {
            'estudiante':   forms.Select(attrs={**WIDGET_SELECT, 'include_blank': 'Sin estudiante'}),
            'titulo':       forms.TextInput(attrs={**WIDGET_INPUT, 'placeholder': 'Ej: Cita con padre de Juan Pérez'}),
            'duracion':     forms.NumberInput(attrs={**WIDGET_INPUT, 'min': '15', 'max': '240', 'value': '60'}),
            'observaciones': forms.Textarea(attrs={**WIDGET_AREA, 'placeholder': 'Notas adicionales...'}),
            'recordar':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        psicologo = kwargs.pop('psicologo', None)
        super().__init__(*args, **kwargs)
        choices = [('', 'Otro (sin color predefinido)')]
        if psicologo:
            tipos = ConfigTipoCita.objects.filter(psicologo=psicologo, activo=True).order_by('orden', 'nombre')
            for t in tipos:
                choices.append((t.nombre, t.nombre))
        self.fields['tipo_cita'].choices = choices
