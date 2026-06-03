def notificaciones_processor(request):
    if request.user.is_authenticated and hasattr(request.user, 'perfil'):
        from matriculas.models import Notificacion
        notificaciones = list(request.user.notificaciones.all()[:10])
        pending = request.user.notificaciones.filter(leida=False).count()
        return {
            'notificaciones': notificaciones,
            'pending_notifications': pending,
        }
    return {'notificaciones': [], 'pending_notifications': 0}
