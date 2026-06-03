from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario, ProcesoPsicologico, ConsejoProceso, HistoriaClinica, Libro, Video, TemaForo, Conversacion, MensajeForo


class PerfilInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name = 'Perfil'


class UsuarioAdmin(UserAdmin):
    inlines = [PerfilInline]


admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'rol')
    list_filter   = ('rol',)
    search_fields = ('usuario__username', 'usuario__first_name')


class ConsejoInline(admin.TabularInline):
    model  = ConsejoProceso
    extra  = 0
    readonly_fields = ('autor', 'fecha')


@admin.register(ProcesoPsicologico)
class ProcesoPsicologicoAdmin(admin.ModelAdmin):
    list_display   = ('numero_identificacion', 'tipo_identificacion', 'nombre_estudiante', 'grado', 'tipo_proceso', 'estado', 'fecha_inicio', 'fecha_fin', 'creado_por')
    list_filter    = ('tipo_proceso', 'estado')
    search_fields  = ('nombre_estudiante', 'grado')
    date_hierarchy = 'fecha_inicio'
    inlines        = [ConsejoInline]


@admin.register(ConsejoProceso)
class ConsejoProcesoAdmin(admin.ModelAdmin):
    list_display = ('proceso', 'autor', 'fecha')
    list_filter  = ('autor',)


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'autor', 'categoria', 'fecha_publicacion', 'agregado_por')
    list_filter   = ('categoria',)
    search_fields = ('titulo', 'autor')


@admin.register(TemaForo)
class TemaForoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'autor', 'fecha')
    list_filter  = ('categoria',)
    search_fields = ('titulo',)


class MensajeInline(admin.TabularInline):
    model  = MensajeForo
    extra  = 0
    readonly_fields = ('autor', 'fecha')


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ('tema', 'profesor', 'fecha_creacion')
    list_filter  = ('tema',)
    search_fields = ('profesor__username', 'profesor__first_name', 'tema__titulo')
    inlines      = [MensajeInline]


@admin.register(MensajeForo)
class MensajeForoAdmin(admin.ModelAdmin):
    list_display = ('conversacion', 'autor', 'texto', 'fecha')
    list_filter  = ('autor',)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'categoria', 'agregado_por', 'fecha_creacion')
    list_filter   = ('categoria',)
    search_fields = ('titulo', 'descripcion')


@admin.register(HistoriaClinica)
class HistoriaClinicaAdmin(admin.ModelAdmin):
    list_display = ('proceso', 'autor', 'fecha')
    list_filter  = ('proceso', 'autor')
    search_fields = ('proceso__nombre_estudiante', 'contenido')
