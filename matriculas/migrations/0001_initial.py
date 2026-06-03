from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PerfilUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(choices=[('psicologo', 'Psicólogo'), ('profesor', 'Profesor')], default='profesor', max_length=20)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Perfil de Usuario', 'verbose_name_plural': 'Perfiles de Usuarios'},
        ),
        migrations.CreateModel(
            name='ProcesoPsicologico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_estudiante', models.CharField(max_length=150, verbose_name='Nombre del Estudiante')),
                ('grado', models.CharField(max_length=10, verbose_name='Grado')),
                ('tipo_proceso', models.CharField(choices=[('vocacional', 'Orientación Vocacional'), ('academico', 'Apoyo Académico'), ('emocional', 'Acompañamiento Emocional'), ('familiar', 'Psicología Familiar')], max_length=20, verbose_name='Tipo de Proceso')),
                ('estado', models.CharField(choices=[('activo', 'Activo'), ('en_curso', 'En Curso'), ('finalizado', 'Finalizado')], default='activo', max_length=20, verbose_name='Estado')),
                ('fecha_inicio', models.DateField(verbose_name='Fecha de Inicio')),
                ('ultima_actualizacion', models.DateField(auto_now=True, verbose_name='Última Actualización')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción del Proceso')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='procesos_creados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Proceso Psicológico', 'verbose_name_plural': 'Procesos Psicológicos', 'ordering': ['-fecha_creacion']},
        ),
        migrations.CreateModel(
            name='ConsejoProceso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField(verbose_name='Consejo')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('proceso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consejos', to='matriculas.procesopsicologico')),
            ],
            options={'verbose_name': 'Consejo', 'verbose_name_plural': 'Consejos', 'ordering': ['-fecha']},
        ),
        migrations.CreateModel(
            name='Libro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título')),
                ('autor', models.CharField(max_length=150, verbose_name='Autor')),
                ('categoria', models.CharField(choices=[('psicologia', 'Psicología'), ('desarrollo', 'Desarrollo'), ('autoayuda', 'Autoayuda'), ('educacion', 'Educación')], max_length=20, verbose_name='Categoría')),
                ('descripcion', models.TextField(verbose_name='Descripción')),
                ('fecha_publicacion', models.DateField(verbose_name='Fecha de Publicación')),
                ('archivo', models.FileField(blank=True, null=True, upload_to='libros/', verbose_name='Archivo PDF')),
                ('color_portada', models.CharField(default='#8b2be2', max_length=7, verbose_name='Color de portada')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('agregado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='libros_agregados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Libro', 'verbose_name_plural': 'Libros', 'ordering': ['-fecha_creacion']},
        ),
        migrations.CreateModel(
            name='TemaForo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=250, verbose_name='Título del Tema')),
                ('categoria', models.CharField(choices=[('emocional', 'Manejo Emocional'), ('motivacion', 'Motivación Académica'), ('convivencia', 'Convivencia Escolar'), ('familias', 'Relación con Familias')], max_length=20, verbose_name='Categoría')),
                ('descripcion', models.TextField(verbose_name='Descripción')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('vistas', models.PositiveIntegerField(default=0)),
                ('reacciones', models.PositiveIntegerField(default=0)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='temas_creados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Tema del Foro', 'verbose_name_plural': 'Temas del Foro', 'ordering': ['-fecha']},
        ),
        migrations.CreateModel(
            name='RespuestaForo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField(verbose_name='Respuesta')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('tema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas', to='matriculas.temaforo')),
            ],
            options={'verbose_name': 'Respuesta del Foro', 'verbose_name_plural': 'Respuestas del Foro', 'ordering': ['fecha']},
        ),
    ]
