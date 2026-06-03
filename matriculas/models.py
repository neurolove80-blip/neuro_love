from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    ROL_CHOICES = [
        ('psicologo', 'Psicólogo'),
        ('profesor',  'Profesor'),
        ('admin',     'Administrador'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol     = models.CharField(max_length=20, choices=ROL_CHOICES, default='profesor')

    def es_psicologo(self):
        return self.rol == 'psicologo'

    def es_admin(self):
        return self.rol == 'admin'

    def tiene_acceso_privilegiado(self):
        return self.rol in ('psicologo', 'admin')

    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.get_rol_display()})"

    class Meta:
        verbose_name        = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'


# ──────────────────────────────────────
#  PROCESOS DE ACOMPAÑAMIENTO
# ──────────────────────────────────────
class ProcesoPsicologico(models.Model):
    TIPO_CHOICES = [
        ('vocacional',  'Orientación Vocacional'),
        ('academico',   'Apoyo Académico'),
        ('emocional',   'Acompañamiento Emocional'),
        ('familiar',    'Psicología Familiar'),
    ]
    ESTADO_CHOICES = [
        ('activo',     'Activo'),
        ('en_curso',   'En Curso'),
        ('finalizado', 'Finalizado'),
    ]
    TIPO_ID_CHOICES = [
        ('CC', 'Cédula de Ciudadanía (CC)'),
        ('TI', 'Tarjeta de Identidad (TI)'),
    ]

    tipo_identificacion   = models.CharField(max_length=2, choices=TIPO_ID_CHOICES, null=True, blank=True, verbose_name='Tipo de Identificación')
    numero_identificacion = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name='Número de Identificación')
    nombre_estudiante     = models.CharField(max_length=150, verbose_name='Nombre del Estudiante')
    grado                 = models.CharField(max_length=10,  verbose_name='Grado')
    tipo_proceso       = models.CharField(max_length=20,  choices=TIPO_CHOICES, verbose_name='Tipo de Proceso')
    estado             = models.CharField(max_length=20,  choices=ESTADO_CHOICES, default='activo', verbose_name='Estado')
    fecha_inicio       = models.DateField(verbose_name='Fecha de Inicio')
    fecha_fin          = models.DateField(null=True, blank=True, verbose_name='Fecha de Fin')
    ultima_actualizacion = models.DateField(auto_now=True, verbose_name='Última Actualización')
    descripcion        = models.TextField(blank=True, verbose_name='Descripción del Proceso')
    creado_por         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='procesos_creados')
    fecha_creacion     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_estudiante} — {self.get_tipo_proceso_display()}"

    def clean(self):
        if self.fecha_fin and self.fecha_inicio:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError({'fecha_fin': 'La fecha de fin debe ser mayor o igual a la fecha de inicio.'})

    class Meta:
        verbose_name        = 'Proceso Psicológico'
        verbose_name_plural = 'Procesos Psicológicos'
        ordering            = ['-fecha_creacion']


class ConsejoProceso(models.Model):
    """Ajustes razonables que los profesores dan sobre un proceso."""
    proceso = models.ForeignKey(ProcesoPsicologico, on_delete=models.CASCADE, related_name='consejos')
    autor   = models.ForeignKey(User, on_delete=models.CASCADE)
    texto   = models.TextField(verbose_name='Ajuste Razonable')
    fecha   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ajuste razonable de {self.autor.get_full_name()} para {self.proceso}"

    class Meta:
        verbose_name        = 'Ajuste Razonable'
        verbose_name_plural = 'Ajustes Razonables'
        ordering            = ['-fecha']


class HistoriaClinica(models.Model):
    """Entradas de historia clínica para un proceso psicológico."""
    proceso  = models.ForeignKey(ProcesoPsicologico, on_delete=models.CASCADE, related_name='historia_clinica')
    contenido = models.TextField(verbose_name='Entrada de Historia Clínica')
    autor    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entradas_historia')
    fecha    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entrada del {self.fecha.strftime('%d/%m/%Y')} — {self.proceso}"

    class Meta:
        verbose_name        = 'Entrada de Historia Clínica'
        verbose_name_plural = 'Entradas de Historia Clínica'
        ordering            = ['fecha']


# ──────────────────────────────────────
#  BIBLIOTECA DIGITAL
# ──────────────────────────────────────
class Libro(models.Model):
    CATEGORIA_CHOICES = [
        ('psicologia', 'Psicología'),
        ('desarrollo', 'Desarrollo'),
        ('autoayuda',  'Autoayuda'),
        ('educacion',  'Educación'),
    ]

    titulo     = models.CharField(max_length=200, verbose_name='Título')
    autor      = models.CharField(max_length=150, verbose_name='Autor')
    categoria  = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoría')
    descripcion = models.TextField(verbose_name='Descripción')
    fecha_publicacion = models.DateField(verbose_name='Fecha de Publicación')
    archivo    = models.FileField(upload_to='libros/', blank=True, null=True, verbose_name='Archivo PDF')
    imagen_portada = models.ImageField(upload_to='libros/covers/', blank=True, null=True, verbose_name='Imagen de portada')
    color_portada = models.CharField(max_length=7, default='#8b2be2', verbose_name='Color de portada (si no hay imagen)')
    agregado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='libros_agregados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} — {self.autor}"

    class Meta:
        verbose_name        = 'Libro'
        verbose_name_plural = 'Libros'
        ordering            = ['-fecha_creacion']


# ──────────────────────────────────────
#  FORO COLABORATIVO
# ──────────────────────────────────────
class TemaForo(models.Model):
    CATEGORIA_CHOICES = [
        ('emocional',   'Manejo Emocional'),
        ('motivacion',  'Motivación Académica'),
        ('convivencia', 'Convivencia Escolar'),
        ('familias',    'Relación con Familias'),
    ]

    titulo      = models.CharField(max_length=250, verbose_name='Título del Tema')
    categoria   = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoría')
    descripcion = models.TextField(verbose_name='Descripción')
    autor       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temas_creados')
    fecha       = models.DateTimeField(auto_now_add=True)
    vistas      = models.PositiveIntegerField(default=0)

    def total_conversaciones(self):
        return self.conversaciones.count()

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name        = 'Tema del Foro'
        verbose_name_plural = 'Temas del Foro'
        ordering            = ['-fecha']


class Conversacion(models.Model):
    tema        = models.ForeignKey(TemaForo, on_delete=models.CASCADE, related_name='conversaciones')
    profesor    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones')
    psicologo   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_como_psicologo', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tema', 'profesor')
        verbose_name        = 'Conversación'
        verbose_name_plural = 'Conversaciones'
        ordering            = ['-fecha_creacion']

    def __str__(self):
        return f"Conversación: {self.tema.titulo} - {self.profesor.get_full_name()}"

    def participantes(self):
        return [self.profesor, self.psicologo] if self.psicologo else [self.profesor]


class MensajeForo(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    autor        = models.ForeignKey(User, on_delete=models.CASCADE)
    texto        = models.TextField(verbose_name='Mensaje')
    fecha        = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Mensaje del Foro'
        verbose_name_plural = 'Mensajes del Foro'
        ordering            = ['fecha']

    def __str__(self):
        return f"Mensaje de {self.autor.get_full_name()} en {self.conversacion}"


# ──────────────────────────────────────
#  CALENDARIO DE CITAS
# ──────────────────────────────────────
class CalendarioConfig(models.Model):
    DIA_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    psicologo = models.OneToOneField(User, on_delete=models.CASCADE, related_name='config_calendario')
    dia_inicio_semana = models.IntegerField(choices=DIA_CHOICES, default=0, verbose_name='Primer día de la semana')
    hora_inicio = models.TimeField(default='07:00', verbose_name='Hora de inicio de atención')
    hora_fin = models.TimeField(default='17:00', verbose_name='Hora de fin de atención')
    
    class Meta:
        verbose_name = 'Configuración del Calendario'
        verbose_name_plural = 'Configuraciones del Calendario'
    
    def __str__(self):
        return f"Configuración de {self.psicologo.get_full_name()}"


class DiaNoHabil(models.Model):
    psicologo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dias_no_habiles')
    fecha = models.DateField(verbose_name='Fecha')
    motivo = models.CharField(max_length=200, verbose_name='Motivo')
    es_recurrente = models.BooleanField(default=False, verbose_name='Se repite anualmente')
    
    class Meta:
        verbose_name = 'Día No Hábil'
        verbose_name_plural = 'Días No Hábiles'
        ordering = ['fecha']
        unique_together = ('psicologo', 'fecha')
    
    def __str__(self):
        return f"{self.fecha} - {self.motivo}"


class Cita(models.Model):
    psicologo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas')
    estudiante = models.ForeignKey(ProcesoPsicologico, on_delete=models.SET_NULL, null=True, blank=True, related_name='citas')
    tipo_cita = models.CharField(max_length=100, verbose_name='Tipo de Cita')
    titulo = models.CharField(max_length=200, verbose_name='Título')
    fecha_hora = models.DateTimeField(verbose_name='Fecha y Hora')
    duracion = models.PositiveIntegerField(default=60, verbose_name='Duración (minutos)')
    color = models.CharField(max_length=7, blank=True, verbose_name='Color')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    recordar = models.BooleanField(default=True, verbose_name='Recordar 1 hora antes')
    notificado = models.BooleanField(default=False, verbose_name='Notificación enviada')
    google_event_id = models.CharField(max_length=200, null=True, blank=True, verbose_name='ID Evento Google Calendar')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.color:
            if self.tipo_cita:
                colores_tipo = {
                    'Reunión talentos humanos': '#27ae60',
                    'Reunión rector': '#e74c3c',
                    'Reunión coordinador/a': '#3498db',
                    'Reunión comité de convivencias': '#f39c12',
                    'Cita padre de familia': '#9b59b6',
                    'Cita estudiante': '#16a085',
                    'Reunión otro psicólogo/a': '#d35400',
                    'Reunión profesores': '#7d3c98',
                }
                self.color = colores_tipo.get(self.tipo_cita, '#8b2be2')
            else:
                self.color = '#8b2be2'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.titulo} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
    
    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['fecha_hora']


class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('cita', 'Recordatorio de Cita'),
        ('sistema', 'Sistema'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sistema')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    enlace = models.CharField(max_length=200, blank=True)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'


class ConfigTipoCita(models.Model):
    psicologo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='config_tipos_cita')
    nombre = models.CharField(max_length=100, verbose_name='Nombre del Tipo')
    color = models.CharField(max_length=7, default='#8b2be2', verbose_name='Color')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name = 'Tipo de Cita'
        verbose_name_plural = 'Tipos de Cita'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


# ──────────────────────────────────────
#  GOOGLE CALENDAR INTEGRATION
# ──────────────────────────────────────
class GoogleCredentials(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_credentials')
    token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_uri = models.CharField(max_length=200, default='https://oauth2.googleapis.com/token')
    client_id = models.CharField(max_length=200)
    client_secret = models.CharField(max_length=200)
    scopes = models.TextField(blank=True)
    expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Credenciales de Google'
        verbose_name_plural = 'Credenciales de Google'

    def __str__(self):
        return f"Google de {self.usuario.username}"


# ──────────────────────────────────────
#  CORREOS CON IA
# ──────────────────────────────────────
class Video(models.Model):
    CATEGORIA_CHOICES = [
        ('psicologia', 'Psicología'),
        ('educacion', 'Educación'),
        ('tutorial', 'Tutorial'),
        ('motivacional', 'Motivacional'),
        ('capacitacion', 'Capacitación'),
    ]

    titulo        = models.CharField(max_length=200, verbose_name='Título')
    url           = models.URLField(verbose_name='URL del video (YouTube)')
    categoria     = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoría')
    descripcion   = models.TextField(verbose_name='Descripción')
    imagen_portada = models.ImageField(upload_to='videos/covers/', blank=True, null=True, verbose_name='Imagen de portada')
    agregado_por  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='videos_agregados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def youtube_id(self):
        import re
        match = re.search(r'(?:v=|youtu\.be/|/embed/|shorts/|live/)([a-zA-Z0-9_-]{11})', self.url)
        return match.group(1) if match else ''

    def thumbnail_url(self):
        vid = self.youtube_id()
        return f'https://img.youtube.com/vi/{vid}/hqdefault.jpg' if vid else ''

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name        = 'Video'
        verbose_name_plural = 'Videos'
        ordering            = ['-fecha_creacion']


class EmailLog(models.Model):
    TONE_CHOICES = [
        ('formal',       'Formal'),
        ('calido',       'Cálido'),
        ('informativo',  'Informativo'),
        ('urgente',      'Urgente'),
    ]

    proceso      = models.ForeignKey(ProcesoPsicologico, on_delete=models.SET_NULL, null=True, related_name='correos', verbose_name='Estudiante')
    subject      = models.CharField(max_length=300, verbose_name='Asunto')
    body         = models.TextField(verbose_name='Cuerpo del Correo')
    tone         = models.CharField(max_length=20, choices=TONE_CHOICES, verbose_name='Tono')
    destinatario = models.EmailField(verbose_name='Correo del Destinatario')
    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='correos_creados')
    created_at   = models.DateTimeField(auto_now_add=True)
    sent         = models.BooleanField(default=False)
    sent_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Registro de Correo'
        verbose_name_plural = 'Registros de Correos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.proceso}"
