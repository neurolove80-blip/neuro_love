import base64
import json
import os
from email.mime.text import MIMEText

import anthropic
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from googleapiclient.discovery import build

from .models import EmailLog, ProcesoPsicologico
from .views_google import get_google_credentials

TONO_DISPLAY = {
    'formal':      'formal y profesional',
    'calido':      'cálido y empático',
    'informativo': 'informativo y claro',
    'urgente':     'urgente pero respetuoso',
}


@login_required
def buscar_estudiante(request):
    """GET /correos/buscar-estudiante/?q=nombre — autocomplete JSON."""
    q = request.GET.get('q', '').strip()
    resultados = []
    if q:
        procesos = (
            ProcesoPsicologico.objects
            .filter(nombre_estudiante__icontains=q)
            .order_by('nombre_estudiante')[:10]
        )
        resultados = [
            {
                'id': p.pk,
                'nombre_estudiante': p.nombre_estudiante,
                'grado': p.grado,
                'numero_identificacion': p.numero_identificacion or '',
                'tipo_proceso': p.get_tipo_proceso_display(),
            }
            for p in procesos
        ]
    return JsonResponse(resultados, safe=False)


@login_required
def nuevo_correo(request):
    """Vista principal para generar y enviar correos con IA."""
    if not request.user.perfil.es_psicologo():
        return HttpResponseForbidden('Acceso denegado.')

    tiene_google = hasattr(request.user, 'google_credentials')
    return render(request, 'matriculas/correos/nuevo.html', {
        'tiene_google': tiene_google,
    })


@login_required
@require_http_methods(['POST'])
def generar_correo(request):
    """POST /correos/generar/ — llama a Claude y devuelve {subject, body}."""
    if not request.user.perfil.es_psicologo():
        return JsonResponse({'error': 'Acceso denegado'}, status=403)

    proceso_id         = request.POST.get('proceso_id', '').strip()
    correo_destinatario = request.POST.get('correo_destinatario', '').strip()
    motivo             = request.POST.get('motivo', '').strip()
    tono               = request.POST.get('tono', 'formal')
    info_adicional     = request.POST.get('info_adicional', '').strip()

    if not proceso_id:
        return JsonResponse({'error': 'Debes seleccionar un estudiante.'}, status=400)
    if not motivo:
        return JsonResponse({'error': 'El motivo del correo es obligatorio.'}, status=400)

    try:
        proceso = ProcesoPsicologico.objects.get(pk=proceso_id)
    except ProcesoPsicologico.DoesNotExist:
        return JsonResponse({'error': 'Estudiante no encontrado.'}, status=404)

    tono_legible = TONO_DISPLAY.get(tono, tono)
    prompt = (
        f'Redacta un correo electrónico para el contexto educativo con la siguiente información:\n\n'
        f'Estudiante: {proceso.nombre_estudiante}\n'
        f'Grado: {proceso.grado}\n'
        f'Tipo de proceso psicológico: {proceso.get_tipo_proceso_display()}\n'
        f'Motivo del correo: {motivo}\n'
        f'Tono solicitado: {tono_legible}\n'
        f'Información adicional: {info_adicional if info_adicional else "Ninguna"}\n\n'
        'Genera el correo completo. '
        'Responde ÚNICAMENTE con un JSON válido con este formato exacto:\n'
        '{"subject": "Asunto del correo aquí", "body": "Cuerpo completo del correo aquí"}'
    )

    try:
        api_key = os.environ.get('ANTHROPIC_API_KEY') or settings.ANTHROPIC_API_KEY
        if not api_key:
            return JsonResponse({'error': 'ANTHROPIC_API_KEY no está configurada. El administrador debe configurarla en el servidor.'}, status=500)
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=1500,
            system=(
                'Eres un asistente de psicología escolar. '
                'Redactas correos profesionales, empáticos y apropiados '
                'para el contexto educativo colombiano.'
            ),
            messages=[{'role': 'user', 'content': prompt}],
        )
        content = response.content[0].text.strip()
        # Eliminar bloques markdown si la IA los incluye
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)
        return JsonResponse({
            'subject': data.get('subject', ''),
            'body':    data.get('body', ''),
        })
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'La IA devolvió una respuesta inesperada. Intenta de nuevo.'},
            status=500,
        )
    except Exception as exc:
        return JsonResponse({'error': f'Error al generar el correo: {exc}'}, status=500)


@login_required
@require_http_methods(['POST'])
def enviar_correo(request):
    """POST /correos/enviar/ — envía por Gmail API y guarda en EmailLog."""
    if not request.user.perfil.es_psicologo():
        return JsonResponse({'error': 'Acceso denegado'}, status=403)

    proceso_id          = request.POST.get('proceso_id', '').strip()
    subject             = request.POST.get('subject', '').strip()
    body                = request.POST.get('body', '').strip()
    tono                = request.POST.get('tono', 'formal')
    correo_destinatario = request.POST.get('correo_destinatario', '').strip()

    if not all([proceso_id, subject, body, correo_destinatario]):
        return JsonResponse({'error': 'Faltan campos obligatorios.'}, status=400)

    try:
        proceso = ProcesoPsicologico.objects.get(pk=proceso_id)
    except ProcesoPsicologico.DoesNotExist:
        return JsonResponse({'error': 'Estudiante no encontrado.'}, status=404)

    creds = get_google_credentials(request.user)
    if not creds:
        return JsonResponse(
            {'error': 'No tienes Google conectado. Ve a Configuración de Google primero.'},
            status=400,
        )

    try:
        service = build('gmail', 'v1', credentials=creds)

        mime_msg = MIMEText(body, 'plain', 'utf-8')
        mime_msg['to']      = correo_destinatario
        mime_msg['subject'] = subject
        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

        service.users().messages().send(userId='me', body={'raw': raw}).execute()

        EmailLog.objects.create(
            proceso=proceso,
            subject=subject,
            body=body,
            tone=tono,
            destinatario=correo_destinatario,
            created_by=request.user,
            sent=True,
            sent_at=timezone.now(),
        )

        return JsonResponse({'ok': True, 'mensaje': 'Correo enviado correctamente.'})
    except Exception as exc:
        return JsonResponse({'error': f'Error al enviar el correo: {exc}'}, status=500)


@login_required
def historial_correos(request):
    """Lista todos los correos enviados, filtrable por nombre de estudiante."""
    if not request.user.perfil.es_psicologo():
        return HttpResponseForbidden('Acceso denegado.')

    q = request.GET.get('q', '').strip()
    correos = EmailLog.objects.filter(created_by=request.user).order_by('-created_at')
    if q:
        correos = correos.filter(proceso__nombre_estudiante__icontains=q)

    return render(request, 'matriculas/correos/historial.html', {
        'correos': correos,
        'q': q,
    })
