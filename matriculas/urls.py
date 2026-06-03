from django.urls import path
from . import views, views_google, views_correos

urlpatterns = [
    # Inicio y auth
    path('',          views.inicio,   name='inicio'),
    path('registro/', views.registro, name='registro'),

    # Procesos (Estudiantes)
    path('estudiantes/',                  views.lista_procesos,   name='lista_procesos'),
    path('estudiantes/nuevo/',            views.crear_proceso,    name='crear_proceso'),
    path('estudiantes/<int:pk>/',         views.detalle_proceso,  name='detalle_proceso'),
    path('estudiantes/<int:pk>/editar/',  views.editar_proceso,   name='editar_proceso'),
    path('estudiantes/<int:pk>/eliminar/',views.eliminar_proceso, name='eliminar_proceso'),
    path('estudiantes/<int:pk>/historia-pdf/', views.descargar_historia_clinica, name='descargar_historia_pdf'),
    path('estudiantes/<int:pk>/analizar/', views.analizar_con_ia, name='analizar_con_ia'),
    path('estudiantes/<int:pk>/analizar-pdf/', views.descargar_analisis_ia_pdf, name='descargar_analisis_ia_pdf'),
    path('estudiantes/<int:pk>/ajustes-pdf/', views.descargar_ajustes_pdf, name='descargar_ajustes_pdf'),

    # Biblioteca (Libros)
    path('biblioteca/',                 views.lista_libros,   name='lista_libros'),
    path('biblioteca/nuevo/',           views.crear_libro,    name='crear_libro'),
    path('biblioteca/<int:pk>/editar/', views.editar_libro,   name='editar_libro'),
    path('biblioteca/<int:pk>/eliminar/',views.eliminar_libro, name='eliminar_libro'),
    path('biblioteca/<int:pk>/descargar/', views.descargar_libro, name='descargar_libro'),

    # Foro
    path('foro/',                              views.lista_foro,              name='lista_foro'),
    path('foro/nuevo/',                        views.crear_tema,              name='crear_tema'),
    path('foro/<int:tema_pk>/',                 views.abrir_conversacion,      name='abrir_conversacion'),
    path('foro/<int:tema_pk>/conversaciones/', views.lista_conversaciones,   name='lista_conversaciones'),
    path('foro/<int:pk>/eliminar/',            views.eliminar_tema,           name='eliminar_tema'),

    # Calendario
    path('calendario/',                       views.calendario,              name='calendario'),
    path('calendario/cita/nueva/',          views.crear_cita,             name='crear_cita'),
    path('calendario/cita/<int:pk>/editar/',views.editar_cita,            name='editar_cita'),
    path('calendario/cita/<int:pk>/eliminar/',views.eliminar_cita,           name='eliminar_cita'),
    path('calendario/dia/<int:pk>/eliminar/',views.eliminar_dia_no_habil,name='eliminar_dia_no_habil'),
    path('calendario/api/citas/',           views.api_citas,             name='api_citas'),
    path('calendario/tipos/',             views.config_tipos_cita,        name='config_tipos_cita'),
    path('calendario/tipos/<int:pk>/eliminar/',views.eliminar_tipo_cita,name='eliminar_tipo_cita'),
    path('calendario/tipos/api/',        views.api_tipos_cita,       name='api_tipos_cita'),
    
    # Videoteca
    path('videoteca/',                 views.lista_videos,   name='lista_videos'),
    path('videoteca/nuevo/',           views.crear_video,    name='crear_video'),
    path('videoteca/<int:pk>/editar/', views.editar_video,   name='editar_video'),
    path('videoteca/<int:pk>/eliminar/',views.eliminar_video, name='eliminar_video'),

    # Notificaciones
    path('notificaciones/<int:pk>/leida/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),

    # Panel de Administración
    path('admin-panel/',                              views.admin_dashboard,      name='admin_dashboard'),
    path('admin-panel/usuarios/',                     views.admin_usuarios,       name='admin_usuarios'),
    path('admin-panel/usuarios/nuevo/',               views.admin_crear_usuario,  name='admin_crear_usuario'),
    path('admin-panel/usuarios/<int:pk>/editar/',     views.admin_editar_usuario, name='admin_editar_usuario'),
    path('admin-panel/usuarios/<int:pk>/toggle/',     views.admin_toggle_usuario, name='admin_toggle_usuario'),
    path('admin-panel/usuarios/<int:pk>/eliminar/',   views.admin_eliminar_usuario, name='admin_eliminar_usuario'),

    # Google Calendar OAuth & Sync
    path('google/auth/',          views_google.google_auth,          name='google_auth'),
    path('google/callback/',      views_google.google_callback,      name='google_callback'),
    path('google/configuracion/', views_google.google_configuracion, name='google_configuracion'),
    path('google/sync-calendar/', views_google.google_sync_calendar, name='google_sync_calendar'),
    path('google/create-event/',  views_google.google_create_event,  name='google_create_event'),

    # Correos con IA
    path('correos/nuevo/',              views_correos.nuevo_correo,     name='nuevo_correo'),
    path('correos/generar/',            views_correos.generar_correo,   name='generar_correo'),
    path('correos/enviar/',             views_correos.enviar_correo,    name='enviar_correo'),
    path('correos/historial/',          views_correos.historial_correos, name='historial_correos'),
    path('correos/buscar-estudiante/',  views_correos.buscar_estudiante, name='buscar_estudiante'),
]
