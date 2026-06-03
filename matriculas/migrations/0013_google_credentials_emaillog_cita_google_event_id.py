from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matriculas', '0012_alter_perfilusuario_rol'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='google_event_id',
            field=models.CharField(
                blank=True, max_length=200, null=True,
                verbose_name='ID Evento Google Calendar'
            ),
        ),
        migrations.CreateModel(
            name='GoogleCredentials',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.TextField(blank=True)),
                ('refresh_token', models.TextField(blank=True)),
                ('token_uri', models.CharField(default='https://oauth2.googleapis.com/token', max_length=200)),
                ('client_id', models.CharField(max_length=200)),
                ('client_secret', models.CharField(max_length=200)),
                ('scopes', models.TextField(blank=True)),
                ('expiry', models.DateTimeField(blank=True, null=True)),
                ('usuario', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='google_credentials',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Credenciales de Google',
                'verbose_name_plural': 'Credenciales de Google',
            },
        ),
        migrations.CreateModel(
            name='EmailLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=300, verbose_name='Asunto')),
                ('body', models.TextField(verbose_name='Cuerpo del Correo')),
                ('tone', models.CharField(
                    choices=[
                        ('formal', 'Formal'),
                        ('calido', 'Cálido'),
                        ('informativo', 'Informativo'),
                        ('urgente', 'Urgente'),
                    ],
                    max_length=20,
                    verbose_name='Tono',
                )),
                ('destinatario', models.EmailField(verbose_name='Correo del Destinatario')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='correos_creados',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('proceso', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='correos',
                    to='matriculas.procesopsicologico',
                    verbose_name='Estudiante',
                )),
            ],
            options={
                'verbose_name': 'Registro de Correo',
                'verbose_name_plural': 'Registros de Correos',
                'ordering': ['-created_at'],
            },
        ),
    ]
