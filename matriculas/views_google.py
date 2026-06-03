import os
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .models import Cita, GoogleCredentials

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send',
]


def _flow_from_env(redirect_uri):
    """Construye el flujo OAuth leyendo credenciales de variables de entorno."""
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    return Flow.from_client_config(
        {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [redirect_uri],
            }
        },
        scopes=SCOPES,
    )


def get_google_credentials(user):
    """Devuelve Credentials válidas para el usuario, renovando el token si venció."""
    try:
        gc = user.google_credentials
    except GoogleCredentials.DoesNotExist:
        return None

    creds = Credentials(
        token=gc.token,
        refresh_token=gc.refresh_token,
        token_uri=gc.token_uri,
        client_id=gc.client_id,
        client_secret=gc.client_secret,
        scopes=gc.scopes.split(',') if gc.scopes else SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        gc.token = creds.token
        gc.expiry = creds.expiry
        gc.save(update_fields=['token', 'expiry'])

    return creds


def _cita_to_google_event(cita):
    """Convierte una Cita al formato de evento de Google Calendar."""
    inicio = cita.fecha_hora
    fin = inicio + timedelta(minutes=cita.duracion)

    description = cita.observaciones or ''
    if cita.estudiante:
        description += (
            f'\nEstudiante: {cita.estudiante.nombre_estudiante}'
            f' — Grado: {cita.estudiante.grado}'
        )

    return {
        'summary': cita.titulo,
        'description': description.strip(),
        'start': {'dateTime': inicio.isoformat(), 'timeZone': 'America/Bogota'},
        'end':   {'dateTime': fin.isoformat(),    'timeZone': 'America/Bogota'},
    }


# ─── OAuth views ─────────────────────────────────────────────────────────────

@login_required
def google_auth(request):
    """Inicia el flujo OAuth 2.0 con Google."""
    if os.environ.get('DEBUG', 'True') == 'True':
        os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

    redirect_uri = os.environ.get(
        'GOOGLE_REDIRECT_URI',
        request.build_absolute_uri('/google/callback/'),
    )
    flow = _flow_from_env(redirect_uri)
    flow.redirect_uri = redirect_uri

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    request.session['google_oauth_state'] = state
    request.session['google_code_verifier'] = getattr(flow, 'code_verifier', None)
    return redirect(authorization_url)


@login_required
def google_callback(request):
    """Recibe el callback de Google y persiste las credenciales."""
    if os.environ.get('DEBUG', 'True') == 'True':
        os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

    state = request.session.get('google_oauth_state')
    redirect_uri = os.environ.get(
        'GOOGLE_REDIRECT_URI',
        request.build_absolute_uri('/google/callback/'),
    )
    flow = _flow_from_env(redirect_uri)
    flow.redirect_uri = redirect_uri

    code_verifier = request.session.get('google_code_verifier')
    if code_verifier:
        flow.code_verifier = code_verifier

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials

        gc, _ = GoogleCredentials.objects.get_or_create(usuario=request.user)
        gc.token         = creds.token
        gc.token_uri     = creds.token_uri
        gc.client_id     = creds.client_id
        gc.client_secret = creds.client_secret
        gc.scopes        = ','.join(creds.scopes) if creds.scopes else ''
        gc.expiry        = creds.expiry
        if creds.refresh_token:
            gc.refresh_token = creds.refresh_token
        gc.save()

        messages.success(request, 'Google Calendar conectado correctamente.')
    except Exception as exc:
        messages.error(request, f'Error al conectar con Google: {exc}')

    return redirect('google_configuracion')


@login_required
def google_configuracion(request):
    """Página de estado y configuración de Google."""
    tiene_credenciales = hasattr(request.user, 'google_credentials')
    return render(request, 'matriculas/google/configuracion.html', {
        'tiene_credenciales': tiene_credenciales,
    })


# ─── Calendar sync views ──────────────────────────────────────────────────────

@login_required
def google_sync_calendar(request):
    """Exporta a Google Calendar todas las Citas que aún no tienen google_event_id."""
    if not request.user.perfil.es_psicologo():
        return HttpResponseForbidden('Acceso denegado.')

    creds = get_google_credentials(request.user)
    if not creds:
        messages.error(request, 'No tienes credenciales de Google. Conéctate primero.')
        return redirect('google_configuracion')

    try:
        service = build('calendar', 'v3', credentials=creds)
        citas_pendientes = Cita.objects.filter(
            psicologo=request.user, google_event_id__isnull=True
        )

        synced = errors = 0
        for cita in citas_pendientes:
            try:
                event = _cita_to_google_event(cita)
                result = service.events().insert(calendarId='primary', body=event).execute()
                cita.google_event_id = result['id']
                cita.save(update_fields=['google_event_id'])
                synced += 1
            except Exception:
                errors += 1

        if errors:
            messages.warning(request, f'Sincronizadas {synced} citas. Errores en {errors}.')
        else:
            messages.success(request, f'{synced} cita(s) sincronizada(s) con Google Calendar.')
    except Exception as exc:
        messages.error(request, f'Error al conectar con Google Calendar: {exc}')

    return redirect('google_configuracion')


@login_required
@require_http_methods(['POST'])
def google_create_event(request):
    """Crea un evento en Google Calendar para una Cita existente (por cita_id)."""
    if not request.user.perfil.es_psicologo():
        return JsonResponse({'error': 'Acceso denegado'}, status=403)

    creds = get_google_credentials(request.user)
    if not creds:
        return JsonResponse({'error': 'Sin credenciales de Google'}, status=400)

    cita_id = request.POST.get('cita_id')
    try:
        cita = Cita.objects.get(pk=cita_id, psicologo=request.user)
    except Cita.DoesNotExist:
        return JsonResponse({'error': 'Cita no encontrada'}, status=404)

    try:
        service = build('calendar', 'v3', credentials=creds)
        event = _cita_to_google_event(cita)
        result = service.events().insert(calendarId='primary', body=event).execute()
        cita.google_event_id = result['id']
        cita.save(update_fields=['google_event_id'])
        return JsonResponse({'google_event_id': result['id']})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)
