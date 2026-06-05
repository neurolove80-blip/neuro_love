from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import anthropic
from .models import ProcesoPsicologico, ConsejoProceso, HistoriaClinica, Libro, Video, TemaForo, Conversacion, MensajeForo, Cita, DiaNoHabil, CalendarioConfig, ConfigTipoCita, Notificacion, PerfilUsuario
from .forms import (RegistroForm, ProcesoForm, ConsejoForm, HistoriaClinicaForm,
                    LibroForm, VideoForm, TemaForoForm, MensajeForoForm, CitaForm, DiaNoHabilForm, CalendarioConfigForm,
                    AdminCrearUsuarioForm, AdminEditarUsuarioForm)


# ── HELPERS ──────────────────────────────────────────────────────────
def es_psicologo(user):
    return hasattr(user, 'perfil') and user.perfil.es_psicologo()


def es_admin(user):
    return hasattr(user, 'perfil') and user.perfil.es_admin()


def tiene_rol_privilegiado(user):
    """Psicólogo O Administrador — pueden gestionar contenido."""
    return hasattr(user, 'perfil') and user.perfil.tiene_acceso_privilegiado()


def crear_notificacion(usuario, tipo, titulo, mensaje, enlace):
    return Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
       enlace=enlace
    )


def notificar_psicologos(tipo, titulo, mensaje, enlace):
    psicologos = User.objects.filter(perfil__rol='psicologo')
    for psicologo in psicologos:
        crear_notificacion(psicologo, tipo, titulo, mensaje, enlace)


def notificar_profesores(tipo, titulo, mensaje, enlace):
    profesores = User.objects.filter(perfil__rol='profesor')
    for profesor in profesores:
        crear_notificacion(profesor, tipo, titulo, mensaje, enlace)


# ── AUTH ─────────────────────────────────────────────────────────────
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido/a, {user.first_name}!')
            return redirect('inicio')
    else:
        form = RegistroForm()
    return render(request, 'matriculas/registro.html', {'form': form})


# ── INICIO ───────────────────────────────────────────────────────────
def inicio(request):
    return render(request, 'matriculas/inicio.html')


# ══════════════════════════════════════════════════════════════════════
#  PROCESOS
# ══════════════════════════════════════════════════════════════════════
@login_required
def lista_procesos(request):
    q        = request.GET.get('q', '')
    sort     = request.GET.get('sort', 'numero_identificacion')
    order    = request.GET.get('order', 'asc')

    procesos = ProcesoPsicologico.objects.filter(
        Q(nombre_estudiante__icontains=q) |
        Q(numero_identificacion__icontains=q) |
        Q(grado__icontains=q) |
        Q(tipo_proceso__icontains=q) |
        Q(estado__icontains=q)
    )

    if sort == 'identificacion':
        sort_field = 'numero_identificacion'
    elif order == 'desc':
        sort_field = f'-{sort}'
    else:
        sort_field = sort

    try:
        procesos = procesos.order_by(sort_field)
    except:
        procesos = procesos.order_by('numero_identificacion')

    return render(request, 'matriculas/lista_estudiantes.html', {
        'procesos': procesos, 'q': q,
        'es_admin': tiene_rol_privilegiado(request.user),
        'sort': sort, 'order': order,
    })


@login_required
def crear_proceso(request):
    if not tiene_rol_privilegiado(request.user):
        messages.error(request, 'Solo el Psicólogo o Administrador puede agregar procesos.')
        return redirect('lista_procesos')
    form = ProcesoForm(request.POST or None)
    if form.is_valid():
        proceso = form.save(commit=False)
        proceso.creado_por = request.user
        proceso.save()
        messages.success(request, '✅ Proceso agregado correctamente.')
        return redirect('lista_procesos')
    return render(request, 'matriculas/crear_estudiante.html', {'form': form, 'titulo': 'Agregar Nuevo Proceso'})


@login_required
def editar_proceso(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    proceso = get_object_or_404(ProcesoPsicologico, pk=pk)
    form    = ProcesoForm(request.POST or None, instance=proceso)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Proceso actualizado.')
        return redirect('lista_procesos')
    return render(request, 'matriculas/crear_estudiante.html', {'form': form, 'titulo': 'Editar Proceso', 'editar': True})


@login_required
def eliminar_proceso(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    proceso = get_object_or_404(ProcesoPsicologico, pk=pk)
    if request.method == 'POST':
        proceso.delete()
        messages.success(request, '🗑️ Proceso eliminado.')
        return redirect('lista_procesos')
    return render(request, 'matriculas/confirmar_eliminar.html', {'objeto': proceso, 'tipo': 'proceso'})


@login_required
def detalle_proceso(request, pk):
    proceso   = get_object_or_404(ProcesoPsicologico, pk=pk)
    consejos  = proceso.consejos.all()
    historia  = proceso.historia_clinica.all() if tiene_rol_privilegiado(request.user) else []
    form      = None
    form_hist = None

    if tiene_rol_privilegiado(request.user):
        form_hist = HistoriaClinicaForm(request.POST or None)
        if request.method == 'POST' and form_hist.is_valid():
            entrada = form_hist.save(commit=False)
            entrada.proceso = proceso
            entrada.autor   = request.user
            entrada.save()
            messages.success(request, '📋 Entrada de historia clínica guardada.')
            return redirect('detalle_proceso', pk=pk)
    elif hasattr(request.user, 'perfil') and request.user.perfil.rol == 'profesor':
        form = ConsejoForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            consejo = form.save(commit=False)
            consejo.proceso = proceso
            consejo.autor   = request.user
            consejo.save()
            messages.success(request, '💡 Ajuste razonable enviado.')
            return redirect('detalle_proceso', pk=pk)

    return render(request, 'matriculas/detalle_proceso.html', {
        'proceso': proceso, 'consejos': consejos, 'historia': historia,
        'form': form, 'form_hist': form_hist,
        'es_admin': tiene_rol_privilegiado(request.user),
    })


# ══════════════════════════════════════════════════════════════════════
#  GEMINI IA
# ══════════════════════════════════════════════════════════════════════
@login_required
def analizar_con_ia(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return JsonResponse({'error': 'Acceso denegado.'}, status=403)

    proceso = get_object_or_404(ProcesoPsicologico, pk=pk)
    historia = proceso.historia_clinica.all()
    consejos = proceso.consejos.all()

    historia_texto = '\n'.join(
        f"[{h.fecha.strftime('%d/%m/%Y')}] {h.contenido}" for h in historia
    )
    consejos_texto = '\n'.join(
        f"- {c.autor.get_full_name()}: {c.texto}" for c in consejos
    )

    if not historia_texto and not consejos_texto and not proceso.descripcion:
        return JsonResponse({
            'error': 'No hay información suficiente para generar un análisis. '
                     'Registra al menos una entrada en la historia clínica o una descripción del proceso.'
        }, status=400)

    historia_texto = historia_texto or 'Sin entradas registradas.'
    consejos_texto = consejos_texto or 'Sin ajustes razonables registrados.'

    prompt = f"""Eres un asistente psicológico especializado en contextos educativos colombianos.
Analiza ÚNICAMENTE la información proporcionada a continuación. No inventes datos, antecedentes, nombres de docentes, ni detalles que no estén explícitamente registrados. Si una sección no tiene información, indícalo claramente en lugar de suponer.

INFORMACIÓN DEL ESTUDIANTE:
- Nombre: {proceso.nombre_estudiante}
- Grado: {proceso.grado}
- Tipo de proceso: {proceso.get_tipo_proceso_display()}
- Estado actual: {proceso.get_estado_display()}
- Descripción inicial: {proceso.descripcion or 'No registrada.'}

HISTORIA CLÍNICA:
{historia_texto}

AJUSTES RAZONABLES DE PROFESORES:
{consejos_texto}

INSTRUCCIÓN IMPORTANTE: Antes de generar el informe, evalúa si las entradas de la historia clínica contienen información clínicamente coherente y relevante (observaciones sobre el estudiante, conductas, emociones, avances, etc.). Si las entradas son incoherentes, sin sentido, pruebas de texto, palabras sueltas o datos que claramente no corresponden a una historia clínica real, responde ÚNICAMENTE con este mensaje exacto:
"DATOS_INCOHERENTES: Las entradas registradas en la historia clínica no contienen información clínica válida para generar un análisis. Por favor registra observaciones reales del proceso del estudiante."

Si la información es válida, proporciona tu análisis con estas secciones exactas, basándote solo en los datos anteriores:
1. **Resumen del estado actual**
2. **Puntos clave identificados**
3. **Sugerencias de próximos pasos**
4. **Señales de alerta** (si no hay, indicar "Ninguna detectada")

Sé conciso, profesional y empático. Máximo 400 palabras."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-haiku-4-5',
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
        )
        texto = message.content[0].text
        if texto.startswith('DATOS_INCOHERENTES:'):
            return JsonResponse({'error': texto[len('DATOS_INCOHERENTES:'):].strip()}, status=400)
        return JsonResponse({'analisis': texto})
    except Exception as e:
        return JsonResponse({'error': f'Error al contactar Claude: {str(e)}'}, status=500)


@login_required
def descargar_analisis_ia_pdf(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from django.http import HttpResponse
    import re
    from datetime import datetime

    proceso = get_object_or_404(ProcesoPsicologico, pk=pk)

    analisis_texto = request.POST.get('analisis', '').strip()
    if not analisis_texto:
        return HttpResponseForbidden('No se recibió el texto del análisis.')

    response = HttpResponse(content_type='application/pdf')
    nombre_archivo = proceso.nombre_estudiante.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="analisis_ia_{nombre_archivo}.pdf"'

    PURPLE = colors.HexColor('#8b2be2')
    LIGHT_PURPLE = colors.HexColor('#f3e8ff')
    MID_PURPLE = colors.HexColor('#d8b4fe')
    BLUE = colors.HexColor('#5b8dee')
    DARK = colors.HexColor('#1a1a2e')
    GRAY = colors.HexColor('#666666')
    LIGHT_GRAY = colors.HexColor('#f8f9fa')

    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=22,
                                  textColor=PURPLE, spaceAfter=4, alignment=TA_LEFT)
    style_subtitle = ParagraphStyle('subtitle', fontName='Helvetica', fontSize=10,
                                     textColor=GRAY, spaceAfter=0)
    style_section = ParagraphStyle('section', fontName='Helvetica-Bold', fontSize=13,
                                    textColor=PURPLE, spaceBefore=18, spaceAfter=8)
    style_body = ParagraphStyle('body', fontName='Helvetica', fontSize=10,
                                 textColor=DARK, leading=16, spaceAfter=6, alignment=TA_JUSTIFY)
    style_bullet = ParagraphStyle('bullet', fontName='Helvetica', fontSize=10,
                                   textColor=DARK, leading=16, leftIndent=14,
                                   spaceAfter=4, bulletIndent=4)
    style_bold_inline = ParagraphStyle('bold_inline', fontName='Helvetica-Bold', fontSize=10,
                                        textColor=DARK, leading=16, spaceAfter=6)
    style_meta_label = ParagraphStyle('meta_label', fontName='Helvetica-Bold', fontSize=9,
                                       textColor=GRAY, spaceAfter=1)
    style_meta_val = ParagraphStyle('meta_val', fontName='Helvetica', fontSize=10,
                                     textColor=DARK, spaceAfter=0)

    def parse_markdown_to_paragraphs(text):
        elements = []
        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                elements.append(Spacer(1, 4))
                continue
            # Encabezados ##
            if stripped.startswith('## ') or stripped.startswith('### '):
                heading = re.sub(r'^#+\s*', '', stripped)
                heading = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', heading)
                elements.append(Paragraph(heading, style_section))
            # Encabezado numerado bold como "1. **Titulo**"
            elif re.match(r'^\d+\.\s+\*\*', stripped):
                clean = re.sub(r'^\d+\.\s+\*\*(.*?)\*\*', r'\1', stripped)
                clean = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean)
                elements.append(Paragraph(clean, style_section))
            # Bullet points
            elif stripped.startswith('- ') or stripped.startswith('* '):
                content = stripped[2:]
                content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
                elements.append(Paragraph(f'• {content}', style_bullet))
            # Línea que empieza con número "1. texto"
            elif re.match(r'^\d+\.\s+', stripped):
                content = re.sub(r'^\d+\.\s+', '', stripped)
                content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
                num = re.match(r'^(\d+)\.', stripped).group(1)
                elements.append(Paragraph(f'{num}. {content}', style_bullet))
            else:
                content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
                elements.append(Paragraph(content, style_body))
        return elements

    story = []

    # ── Cabecera ──
    header_data = [[
        Paragraph('<b>Analisis con Inteligencia Artificial</b>',
                  ParagraphStyle('hdr', fontName='Helvetica-Bold', fontSize=20,
                                  textColor=colors.white, leading=24)),
        Paragraph(f'Generado por Claude<br/>{datetime.now().strftime("%d/%m/%Y %H:%M")}',
                  ParagraphStyle('hdr2', fontName='Helvetica', fontSize=9,
                                  textColor=colors.HexColor('#e9d5ff'), alignment=2, leading=14)),
    ]]
    header_table = Table(header_data, colWidths=[None, 4.5*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PURPLE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (0, -1), 18),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 16),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 18))

    # ── Tabla de datos del estudiante ──
    estado_map = {'activo': 'Activo', 'en_curso': 'En Curso', 'finalizado': 'Finalizado'}
    estado_display = estado_map.get(proceso.estado, proceso.estado)

    info_data = [
        [Paragraph('<b>Estudiante</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(proceso.nombre_estudiante, ParagraphStyle('v', fontName='Helvetica-Bold', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Grado</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(proceso.grado, ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Tipo de Proceso</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(proceso.get_tipo_proceso_display(), ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Estado</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(estado_display, ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Identificación</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(f'{proceso.tipo_identificacion} {proceso.numero_identificacion}', ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
    ]

    info_table = Table(info_data, colWidths=[4.5*cm, None])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_PURPLE),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT_PURPLE, colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.4, MID_PURPLE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    # ── Análisis de IA ──
    story.append(HRFlowable(width='100%', thickness=0.5, color=MID_PURPLE, spaceAfter=4))
    story.append(Paragraph('Análisis Generado por IA', style_section))
    story.append(HRFlowable(width='100%', thickness=0.5, color=MID_PURPLE, spaceAfter=10))

    story.extend(parse_markdown_to_paragraphs(analisis_texto))

    # ── Pie de página ──
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width='100%', thickness=1, color=MID_PURPLE, spaceAfter=8))
    story.append(Paragraph(
        f'Documento generado por NeuroClick · {datetime.now().strftime("%d/%m/%Y")} · Solo para uso interno',
        ParagraphStyle('footer', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return response


@login_required
def descargar_ajustes_pdf(request, pk):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, Image as RLImage
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from django.http import HttpResponse
    from datetime import datetime
    import os

    proceso  = get_object_or_404(ProcesoPsicologico, pk=pk)
    ajustes  = proceso.consejos.select_related('autor').all()

    PURPLE      = colors.HexColor('#8b2be2')
    LIGHT_PURPLE= colors.HexColor('#f3e8ff')
    MID_PURPLE  = colors.HexColor('#d8b4fe')
    DARK        = colors.HexColor('#1a1a2e')
    GRAY        = colors.HexColor('#666666')
    LIGHT_GRAY  = colors.HexColor('#f8f9fa')
    AMBER       = colors.HexColor('#fff8e1')
    AMBER_BORDER= colors.HexColor('#ffd54f')

    response = HttpResponse(content_type='application/pdf')
    nombre_archivo = proceso.nombre_estudiante.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="ajustes_razonables_{nombre_archivo}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )

    style_section = ParagraphStyle('section', fontName='Helvetica-Bold', fontSize=12,
                                    textColor=PURPLE, spaceBefore=14, spaceAfter=6)
    style_body    = ParagraphStyle('body', fontName='Helvetica', fontSize=10,
                                   textColor=DARK, leading=16, spaceAfter=4, alignment=TA_JUSTIFY)
    style_autor   = ParagraphStyle('autor', fontName='Helvetica-Oblique', fontSize=9,
                                   textColor=GRAY, spaceAfter=0)
    style_empty   = ParagraphStyle('empty', fontName='Helvetica-Oblique', fontSize=10,
                                   textColor=GRAY, alignment=TA_CENTER)

    story = []

    # ── Logo ──
    logo_path = os.path.join(settings.MEDIA_ROOT, 'libros', 'LOGO_COSFA.png')
    if os.path.exists(logo_path):
        logo = RLImage(logo_path, width=70, height=35)
        story.append(logo)
        story.append(Spacer(1, 10))

    # ── Cabecera ──
    header_data = [[
        Paragraph('<b>Ajustes Razonables de Profesores</b>',
                  ParagraphStyle('hdr', fontName='Helvetica-Bold', fontSize=18,
                                  textColor=colors.white, leading=22)),
        Paragraph(f'NeuroClick<br/>{datetime.now().strftime("%d/%m/%Y %H:%M")}',
                  ParagraphStyle('hdr2', fontName='Helvetica', fontSize=9,
                                  textColor=colors.HexColor('#e9d5ff'), alignment=2, leading=14)),
    ]]
    header_table = Table(header_data, colWidths=[None, 4.5*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PURPLE),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING',   (0, 0), (0, -1), 18),
        ('RIGHTPADDING',  (-1, 0), (-1, -1), 16),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    # ── Tabla de datos del estudiante ──
    estado_map = {'activo': 'Activo', 'en_curso': 'En Curso', 'finalizado': 'Finalizado'}
    info_data = [
        [Paragraph('<b>Estudiante</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(proceso.nombre_estudiante, ParagraphStyle('v', fontName='Helvetica-Bold', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Grado</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(proceso.grado, ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Tipo de Proceso</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(proceso.get_tipo_proceso_display(), ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Estado</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(estado_map.get(proceso.estado, proceso.estado), ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
        [Paragraph('<b>Identificación</b>', ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=9, textColor=GRAY)),
         Paragraph(f'{proceso.tipo_identificacion} {proceso.numero_identificacion}', ParagraphStyle('v', fontName='Helvetica', fontSize=10, textColor=DARK))],
    ]
    info_table = Table(info_data, colWidths=[4.5*cm, None])
    info_table.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT_PURPLE, colors.white]),
        ('GRID',           (0, 0), (-1, -1), 0.4, MID_PURPLE),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',     (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 7),
        ('LEFTPADDING',    (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    # ── Sección de ajustes ──
    story.append(HRFlowable(width='100%', thickness=0.5, color=MID_PURPLE, spaceAfter=4))
    story.append(Paragraph(f'Ajustes Razonables Registrados ({ajustes.count()})', style_section))
    story.append(HRFlowable(width='100%', thickness=0.5, color=MID_PURPLE, spaceAfter=12))

    page_width = letter[0] - 4.4*cm

    if ajustes.exists():
        for i, ajuste in enumerate(ajustes, 1):
            nombre_autor = ajuste.autor.get_full_name() or ajuste.autor.username
            fecha_str    = ajuste.fecha.strftime('%d/%m/%Y %H:%M')
            item_data = [
                [Paragraph(f'<b>{i}. {ajuste.texto}</b>' if False else ajuste.texto, style_body)],
                [Paragraph(f'— {nombre_autor} · {fecha_str}', style_autor)],
            ]
            item_table = Table(item_data, colWidths=[page_width])
            item_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_PURPLE),
                ('LEFTPADDING',   (0, 0), (-1, -1), 12),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
                ('TOPPADDING',    (0, 0), (0, 0),   10),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
                ('TOPPADDING',    (0, 1), (-1, -1),  2),
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('LINEABOVE',     (0, 0), (-1, 0),  1.5, PURPLE),
            ]))
            story.append(Paragraph(f'<b>Ajuste {i}</b>', ParagraphStyle('num', fontName='Helvetica-Bold', fontSize=10, textColor=PURPLE, spaceAfter=2)))
            story.append(item_table)
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph('Aún no hay ajustes razonables registrados para este proceso.', style_empty))

    # ── Pie de página ──
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width='100%', thickness=1, color=MID_PURPLE, spaceAfter=8))
    story.append(Paragraph(
        f'Documento generado por NeuroClick · {datetime.now().strftime("%d/%m/%Y")} · Solo para uso interno',
        ParagraphStyle('footer', fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return response


# ══════════════════════════════════════════════════════════════════════
#  BIBLIOTECA
# ══════════════════════════════════════════════════════════════════════
@login_required
def lista_libros(request):
    q      = request.GET.get('q', '')
    libros = Libro.objects.filter(titulo__icontains=q)
    return render(request, 'matriculas/lista_cursos.html', {
        'libros': libros, 'q': q,
        'es_admin': tiene_rol_privilegiado(request.user),
    })


@login_required
def descargar_libro(request, pk):
    """Cualquier usuario logueado puede descargar."""
    from django.http import FileResponse, HttpResponse
    libro = get_object_or_404(Libro, pk=pk)
    if libro.archivo:
        try:
            url = libro.archivo.url
        except Exception:
            url = ''
        # Almacenamiento en la nube (Cloudinary en Railway): redirigir a la URL
        # del archivo y forzar la descarga con la transformación fl_attachment.
        # Abrir el archivo en el servidor (.open) falla con Cloudinary -> error 500.
        if 'res.cloudinary.com' in url:
            if '/upload/' in url and 'fl_attachment' not in url:
                url = url.replace('/upload/', '/upload/fl_attachment/', 1)
            return redirect(url)
        # Almacenamiento local (desarrollo): servir el archivo directamente.
        if url:
            return FileResponse(libro.archivo.open('rb'), as_attachment=True)
    # Si no hay archivo, devolver un .txt con info del libro
    contenido = (
        f"TÍTULO: {libro.titulo}\n"
        f"AUTOR: {libro.autor}\n"
        f"CATEGORÍA: {libro.get_categoria_display()}\n"
        f"FECHA: {libro.fecha_publicacion}\n\n"
        f"DESCRIPCIÓN:\n{libro.descripcion}\n\n"
        "---\nDescargado desde NeuroClick © 2025"
    )
    response = HttpResponse(contenido, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{libro.titulo}.txt"'
    return response


@login_required
def crear_libro(request):
    if not tiene_rol_privilegiado(request.user):
        messages.error(request, 'Solo el Psicólogo o Administrador puede agregar libros.')
        return redirect('lista_libros')
    form = LibroForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        libro = form.save(commit=False)
        libro.agregado_por = request.user
        libro.save()
        messages.success(request, '✅ Libro agregado a la biblioteca.')
        return redirect('lista_libros')
    return render(request, 'matriculas/crear_curso.html', {'form': form, 'titulo': 'Agregar Libro', 'volver_url': 'lista_libros'})


@login_required
def editar_libro(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    libro = get_object_or_404(Libro, pk=pk)
    form  = LibroForm(request.POST or None, request.FILES or None, instance=libro)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Libro actualizado.')
        return redirect('lista_libros')
    return render(request, 'matriculas/crear_curso.html', {'form': form, 'titulo': 'Editar Libro', 'editar': True, 'volver_url': 'lista_libros'})


@login_required
def eliminar_libro(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    libro = get_object_or_404(Libro, pk=pk)
    if request.method == 'POST':
        libro.delete()
        messages.success(request, '🗑️ Libro eliminado.')
        return redirect('lista_libros')
    return render(request, 'matriculas/confirmar_eliminar.html', {'objeto': libro, 'tipo': 'libro'})


# ══════════════════════════════════════════════════════════════════════
#  VIDEOTECA
# ══════════════════════════════════════════════════════════════════════
@login_required
def lista_videos(request):
    q      = request.GET.get('q', '')
    videos = Video.objects.filter(titulo__icontains=q)
    return render(request, 'matriculas/lista_videos.html', {
        'videos': videos, 'q': q,
        'es_admin': tiene_rol_privilegiado(request.user),
    })


@login_required
def crear_video(request):
    if not tiene_rol_privilegiado(request.user):
        messages.error(request, 'Solo el Psicólogo o Administrador puede agregar videos.')
        return redirect('lista_videos')
    form = VideoForm(request.POST or None)
    if form.is_valid():
        video = form.save(commit=False)
        video.agregado_por = request.user
        video.save()
        messages.success(request, '✅ Video agregado a la videoteca.')
        return redirect('lista_videos')
    return render(request, 'matriculas/crear_curso.html', {'form': form, 'titulo': 'Agregar Video', 'volver_url': 'lista_videos'})


@login_required
def editar_video(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    video = get_object_or_404(Video, pk=pk)
    form  = VideoForm(request.POST or None, instance=video)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Video actualizado.')
        return redirect('lista_videos')
    return render(request, 'matriculas/crear_curso.html', {'form': form, 'titulo': 'Editar Video', 'editar': True, 'volver_url': 'lista_videos'})


@login_required
def eliminar_video(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    video = get_object_or_404(Video, pk=pk)
    if request.method == 'POST':
        video.delete()
        messages.success(request, '🗑️ Video eliminado.')
        return redirect('lista_videos')
    return render(request, 'matriculas/confirmar_eliminar.html', {'objeto': video, 'tipo': 'video'})


# ══════════════════════════════════════════════════════════════════════
#  FORO
# ══════════════════════════════════════════════════════════════════════
@login_required
def lista_foro(request):
    es_admin = tiene_rol_privilegiado(request.user)
    
    if es_admin:
        temas = TemaForo.objects.select_related('autor', 'autor__perfil').order_by('-fecha')
        temas_conversaciones = []
        for tema in temas:
            conversaciones = Conversacion.objects.filter(tema=tema).select_related('profesor')
            temas_conversaciones.append({
                'tema': tema,
                'conversaciones': list(conversaciones),
                'total_mensajes': sum(c.mensajes.count() for c in conversaciones)
            })
        return render(request, 'matriculas/lista_foro.html', {
            'temas_conversaciones': temas_conversaciones,
            'es_admin': es_admin,
        })
    else:
        temas = TemaForo.objects.filter(
            Q(autor=request.user) | Q(autor__perfil__rol='psicologo')
        ).select_related('autor', 'autor__perfil').order_by('-fecha')
        mis_temas = []
        for tema in temas:
            try:
                conversacion = Conversacion.objects.get(tema=tema, profesor=request.user)
                tema.mi_conversacion = conversacion
                tema.mensajes_count = conversacion.mensajes.count()
            except Conversacion.DoesNotExist:
                tema.mi_conversacion = None
                tema.mensajes_count = 0
            mis_temas.append(tema)
        return render(request, 'matriculas/lista_foro.html', {
            'mis_temas': mis_temas,
            'es_admin': es_admin,
        })


@login_required
def crear_tema(request):
    form = TemaForoForm(request.POST or None)
    if form.is_valid():
        tema = form.save(commit=False)
        tema.autor = request.user
        tema.save()
        
        if not tiene_rol_privilegiado(request.user):
            from .models import PerfilUsuario
            psicologo_profile = PerfilUsuario.objects.filter(rol='psicologo').first()
            psicologo_user = psicologo_profile.usuario if psicologo_profile else None
            conversacion = Conversacion.objects.create(
                tema=tema,
                profesor=request.user,
                psicologo=psicologo_user
            )
            if psicologo_user:
                crear_notificacion(
                    psicologo_user, 'sistema',
                    f'Nueva pregunta en el foro',
                    f'{request.user.get_full_name()} hizo una pregunta: {tema.titulo}',
                    f'/foro/{tema.pk}/?conversacion={conversacion.pk}'
                )
            else:
                notificar_psicologos(
                    'sistema',
                    f'Nueva pregunta en el foro',
                    f'{request.user.get_full_name()} hizo una pregunta: {tema.titulo}',
                    f'/foro/{tema.pk}/'
                )
            messages.success(request, '✅ Pregunta creada. Conversación iniciada con el psicólogo.')
            return redirect(f'/foro/{tema.pk}/?conversacion={conversacion.pk}')
        else:
            notificar_profesores(
                'sistema',
                f'Nuevo tema en el foro',
                f'{request.user.get_full_name()} creó: {tema.titulo}',
                f'/foro/{tema.pk}/'
            )
        
        messages.success(request, '✅ Tema creado en el foro.')
        return redirect('lista_foro')
    return render(request, 'matriculas/crear_tema.html', {'form': form})


@login_required
def abrir_conversacion(request, tema_pk):
    tema = get_object_or_404(TemaForo, pk=tema_pk)
    es_admin = tiene_rol_privilegiado(request.user)

    conversacion_id = request.GET.get('conversacion')
    
    if es_admin:
        if conversacion_id:
            conversacion = get_object_or_404(Conversacion, pk=conversacion_id, tema=tema)
        else:
            if tema.autor == request.user:
                conversacion = Conversacion.objects.filter(tema=tema, profesor__perfil__rol='profesor').first()
            else:
                conversacion = Conversacion.objects.filter(tema=tema, profesor=tema.autor).first()
            if not conversacion:
                conversacion = Conversacion.objects.filter(tema=tema).first()
            if not conversacion:
                return redirect('lista_conversaciones', tema_pk=tema.pk)
    else:
        if conversacion_id:
            conversacion = get_object_or_404(
                Conversacion, 
                pk=conversacion_id, 
                tema=tema,
                profesor=request.user
            )
        else:
            conversacion = Conversacion.objects.filter(
                tema=tema,
                profesor=request.user
            ).first()
            if not conversacion:
                psicologo_profile = None
                try:
                    from .models import PerfilUsuario
                    psicologo_profile = PerfilUsuario.objects.filter(rol='psicologo').first()
                except:
                    pass
                psicologo_user = psicologo_profile.usuario if psicologo_profile else None
                conversacion = Conversacion.objects.create(
                    tema=tema,
                    profesor=request.user,
                    psicologo=psicologo_user
                )
                messages.success(request, '✅ Conversación iniciada.')
    
    mensajes = conversacion.mensajes.select_related('autor', 'autor__perfil').order_by('fecha')
    
    form = MensajeForoForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.conversacion = conversacion
            mensaje.autor = request.user
            mensaje.save()
            
            if tiene_rol_privilegiado(request.user):
                if conversacion.profesor:
                    crear_notificacion(
                        conversacion.profesor, 'sistema',
                        f'Respuesta en: {tema.titulo}',
                        f'{request.user.get_full_name()} respondió en el foro',
                        f'/foro/{tema.pk}/?conversacion={conversacion.pk}'
                    )
                else:
                    notificar_profesores(
                        'sistema',
                        f'Respuesta en: {tema.titulo}',
                        f'{request.user.get_full_name()} respondió en el foro',
                        f'/foro/{tema.pk}/'
                    )
            else:
                if conversacion.psicologo:
                    crear_notificacion(
                        conversacion.psicologo, 'sistema',
                        f'Respuesta en: {tema.titulo}',
                        f'{request.user.get_full_name()} respondió en el foro',
                        f'/foro/{tema.pk}/?conversacion={conversacion.pk}'
                    )
                notificar_psicologos(
                    'sistema',
                    f'Respuesta en: {tema.titulo}',
                    f'{request.user.get_full_name()} respondió en el foro',
                    f'/foro/{tema.pk}/'
                )
            
            messages.success(request, '✅ Mensaje enviado.')
            return redirect('abrir_conversacion', tema_pk=tema.pk)
    
    return render(request, 'matriculas/conversacion.html', {
        'tema': tema,
        'conversacion': conversacion,
        'mensajes': mensajes,
        'form': form,
        'es_admin': es_admin,
    })


@login_required
def lista_conversaciones(request, tema_pk):
    tema = get_object_or_404(TemaForo, pk=tema_pk)
    es_admin = tiene_rol_privilegiado(request.user)

    if not es_admin:
        return HttpResponseForbidden('Acceso denegado.')

    conversaciones = Conversacion.objects.filter(tema=tema).select_related('profesor')
    return render(request, 'matriculas/lista_conversaciones.html', {
        'tema': tema,
        'conversaciones': conversaciones,
    })


@login_required
def detalle_tema(request, pk):
    tema = get_object_or_404(TemaForo, pk=pk)
    es_admin = tiene_rol_privilegiado(request.user)

    if not es_admin:
        puede_ver = tema.autor == request.user or tema.autor.perfil.es_psicologo()
        if not puede_ver:
            return HttpResponseForbidden('Acceso denegado.')
    
    return redirect('abrir_conversacion', tema_pk=pk)


@login_required
def eliminar_tema(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    tema = get_object_or_404(TemaForo, pk=pk)
    if request.method == 'POST':
        tema.delete()
        messages.success(request, '🗑️ Tema eliminado.')
        return redirect('lista_foro')
    return render(request, 'matriculas/confirmar_eliminar.html', {'objeto': tema, 'tipo': 'tema'})


@login_required
def descargar_historia_clinica(request, pk):
    if not tiene_rol_privilegiado(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from django.http import HttpResponse
    from PIL import Image as PILImage
    import os
    
    proceso = get_object_or_404(ProcesoPsicologico, pk=pk)
    historia = proceso.historia_clinica.all()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="historia_clinica_{proceso.nombre_estudiante.replace(" ", "_")}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    margin = 50
    page_num = 1
    
    # Logo with transparency blended onto white background
    logo_path = os.path.join(settings.MEDIA_ROOT, 'libros', 'LOGO_COSFA.png')
    logo_width = 80
    logo_height = 40
    logo_reader = None
    if os.path.exists(logo_path):
        pil_img = PILImage.open(logo_path).convert('RGBA')
        white_bg = PILImage.new('RGBA', pil_img.size, (255, 255, 255, 255))
        blended = PILImage.alpha_composite(white_bg, pil_img).convert('RGB')
        logo_reader = ImageReader(blended)
    
    def draw_header(y_pos):
        nonlocal page_num
        if logo_reader:
            p.drawImage(logo_reader, width - margin - logo_width, height - margin - 5,
                       width=logo_width, height=logo_height, preserveAspectRatio=True)
        p.setFont("Helvetica-Bold", 20)
        p.setFillColor(colors.HexColor("#8b2be2"))
        p.drawString(margin, height - margin - 12, "Historia Clínica")
        p.setStrokeColor(colors.HexColor("#8b2be2"))
        p.setLineWidth(2)
        p.line(margin, height - margin - 22, width - margin, height - margin - 22)
        p.setFillColor(colors.black)
        # Page number
        p.setFont("Helvetica", 8)
        p.setFillColor(colors.gray)
        p.drawRightString(width - margin, 30, f"Página {page_num}")
        p.setFillColor(colors.black)
        return y_pos - 35
    
    def draw_footer(y_pos):
        p.setStrokeColor(colors.HexColor("#8b2be2"))
        p.setLineWidth(0.5)
        p.line(margin, 40, width - margin, 40)
        p.setFont("Helvetica", 7)
        p.setFillColor(colors.gray)
        p.drawString(margin, 30, "NeuroClick — Plataforma de Psicología Educativa")
        p.setFillColor(colors.black)
    
    def check_page_break(y_pos, needed=60):
        if y_pos < needed:
            draw_footer(y_pos)
            p.showPage()
            nonlocal page_num
            page_num += 1
            return height - margin
        return y_pos
    
    y = height - margin
    y = draw_header(y)
    
    # Student info
    info_y = y - 5
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin + 10, info_y - 5, proceso.nombre_estudiante)
    p.setFont("Helvetica", 11)
    info_items = [
        f"Identificación: {proceso.tipo_identificacion} {proceso.numero_identificacion}",
        f"Grado: {proceso.grado}",
        f"Estado: {proceso.get_estado_display()}",
    ]
    for i, item in enumerate(info_items):
        p.drawString(margin + 10, info_y - 22 - i*14, item)
    
    y = info_y - 100
    
    if historia:
        y = check_page_break(y, 100)
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(colors.HexColor("#8b2be2"))
        p.drawString(margin, y, f"Entradas de Historia Clínica ({historia.count()})")
        y -= 25
        
        for idx, h in enumerate(historia):
            y = check_page_break(y, 120)
            
            # Entry header
            p.setFillColor(colors.HexColor("#5b8dee"))
            p.setFont("Helvetica-Bold", 11)
            fecha_str = h.fecha.strftime('%d/%m/%Y %H:%M')
            autor_nombre = h.autor.get_full_name() if h.autor else "Psicólogo"
            p.drawString(margin + 10, y - 14, f"#{idx+1}  {fecha_str}  —  {autor_nombre}")
            y -= 28
            
            # Content
            p.setFillColor(colors.black)
            p.setFont("Helvetica", 10)
            contenido = h.contenido
            line_width = 95
            paragraphs = contenido.split('\n')
            
            for para in paragraphs:
                if para.strip():
                    words = para.split()
                    line = ''
                    for word in words:
                        test_line = line + ' ' + word if line else word
                        if len(test_line) > line_width:
                            y = check_page_break(y, 40)
                            p.drawString(margin + 10, y, line)
                            y -= 12
                            line = word
                        else:
                            line = test_line
                    if line:
                        y = check_page_break(y, 40)
                        p.drawString(margin + 10, y, line)
                        y -= 12
                else:
                    y -= 8
            
            y -= 12
    else:
        p.setFont("Helvetica", 11)
        p.setFillColor(colors.gray)
        p.drawString(margin, y, "No hay entradas en la historia clínica.")
    
    draw_footer(y)
    p.showPage()
    p.save()
    return response


# ══════════════════════════════════════════════════════════════════════
#  CALENDARIO DE CITAS
# ══════════════════════════════════════════════════════════════════════
import calendar
from datetime import datetime, timedelta

@login_required
def calendario(request):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    año = int(request.GET.get('año', datetime.now().year))
    mes = int(request.GET.get('mes', datetime.now().month))
    
    cita_form = CitaForm(request.POST or None)
    dia_form = DiaNoHabilForm(request.POST or None)
    config_form = CalendarioConfigForm(request.POST or None)
    
    try:
        config = request.user.config_calendario
    except CalendarioConfig.DoesNotExist:
        config = None
    
    if request.method == 'POST':
        if 'crear_cita' in request.POST:
            cita_form = CitaForm(request.POST)
            if cita_form.is_valid():
                cita = cita_form.save(commit=False)
                cita.psicologo = request.user
                cita.save()
                google_synced = False
                try:
                    from .views_google import get_google_credentials, _cita_to_google_event
                    from googleapiclient.discovery import build as gapi_build
                    creds = get_google_credentials(request.user)
                    if creds:
                        service = gapi_build('calendar', 'v3', credentials=creds)
                        result = service.events().insert(
                            calendarId='primary',
                            body=_cita_to_google_event(cita),
                        ).execute()
                        cita.google_event_id = result['id']
                        cita.save(update_fields=['google_event_id'])
                        google_synced = True
                except Exception:
                    pass
                if google_synced:
                    messages.success(request, '✅ Cita agendada y sincronizada con Google Calendar.')
                else:
                    messages.success(request, '✅ Cita agendada correctamente.')
                return redirect('calendario')
        elif 'crear_dia_no_habil' in request.POST:
            dia_form = DiaNoHabilForm(request.POST)
            if dia_form.is_valid():
                dia = dia_form.save(commit=False)
                dia.psicologo = request.user
                dia.save()
                messages.success(request, '✅ Día no hábil agregado.')
                return redirect('calendario')
        elif 'guardar_config' in request.POST:
            config_form = CalendarioConfigForm(request.POST)
            if config_form.is_valid():
                if config:
                    config_form = CalendarioConfigForm(request.POST, instance=config)
                    config_form.save()
                else:
                    config = config_form.save(commit=False)
                    config.psicologo = request.user
                    config.save()
                messages.success(request, '✅ Configuración guardada.')
                return redirect('calendario')
    
    cal = calendar.Calendar(firstweekday=config.dia_inicio_semana if config else 0)
    dias_mes = cal.monthdayscalendar(año, mes)
    
    dias_no_habiles = set()
    dias_no_habiles_recurrentes = set()
    
    dias_db = DiaNoHabil.objects.filter(psicologo=request.user)
    for d in dias_db:
        if d.es_recurrente:
            dias_no_habiles_recurrentes.add((d.fecha.month, d.fecha.day))
        else:
            dias_no_habiles.add((d.fecha.year, d.fecha.month, d.fecha.day))
    
    meses_es = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
            7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
    nombre_mes = meses_es.get(mes, calendar.month_name[mes])
    meses = [(i, calendar.month_name[i]) for i in range(1, 13)]
    
    citas = Cita.objects.filter(
        psicologo=request.user,
        fecha_hora__year=año,
        fecha_hora__month=mes
    ).order_by('fecha_hora')
    
    dias_no_habiles_all = DiaNoHabil.objects.filter(psicologo=request.user)
    
    tipos_cita = ConfigTipoCita.objects.filter(psicologo=request.user, activo=True).order_by('orden', 'nombre')
    
    return render(request, 'matriculas/calendario.html', {
        'año': año,
        'mes': mes,
        'dias_mes': dias_mes,
        'nombre_mes': nombre_mes,
        'meses': meses,
        'citas': citas,
        'dias_no_habiles': dias_no_habiles,
        'dias_no_habiles_recurrentes': dias_no_habiles_recurrentes,
        'dias_no_habiles_all': dias_no_habiles_all,
        'config': config,
        'cita_form': cita_form,
        'dia_form': dia_form,
        'config_form': config_form,
        'tipos_cita': tipos_cita,
        'year': datetime.now().year,
        'month': datetime.now().month,
    })


@login_required
def crear_cita(request):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    estudiantes = ProcesoPsicologico.objects.all().order_by('nombre_estudiante')
    
    if request.method == 'POST':
        tipo_cita = request.POST.get('tipo_cita', '')
        
        fecha = request.POST.get('fecha', '')
        hora = request.POST.get('hora', '09:00')
        
        if tipo_cita:
            titulo = tipo_cita
        else:
            titulo = request.POST.get('titulo', 'Sin título')
        
        duracion = request.POST.get('duracion', '60')
        try:
            duracion = int(duracion)
        except:
            duracion = 60
        
        recordar = request.POST.get('recordar') == 'on'
        
        estudiante_id = request.POST.get('estudiante', '')
        estudiante = None
        if estudiante_id:
            try:
                estudiante = ProcesoPsicologico.objects.get(pk=estudiante_id)
            except:
                pass
        
        observaciones = request.POST.get('observaciones', '')
        
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
        
        from datetime import datetime
        fecha_hora_dt = None
        if fecha and hora:
            try:
                fecha_hora_str = f"{fecha} {hora}"
                fecha_hora_dt = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
            except:
                pass
        elif fecha:
            try:
                fecha_hora_dt = datetime.strptime(fecha, '%Y-%m-%d')
            except:
                pass
        
        if not fecha_hora_dt:
            messages.error(request, 'La fecha y hora es obligatoria.')
            form = CitaForm(initial={'fecha_hora': fecha}, psicologo=request.user)
            return render(request, 'matriculas/crear_cita.html', {'form': form, 'titulo': 'Nueva Cita', 'estudiantes': estudiantes})
        
        if 'Reunión con' in tipo_cita:
            color = '#7d3c98'
        else:
            color = colores_tipo.get(tipo_cita, '#8b2be2')
        
        cita = Cita.objects.create(
            psicologo=request.user,
            estudiante=estudiante,
            tipo_cita=tipo_cita,
            titulo=titulo,
            fecha_hora=fecha_hora_dt,
            duracion=duracion,
            color=color,
            observaciones=observaciones,
            recordar=recordar
        )

        # Sincronizar con Google Calendar si hay credenciales
        google_synced = False
        try:
            from .views_google import get_google_credentials, _cita_to_google_event
            from googleapiclient.discovery import build as gapi_build
            creds = get_google_credentials(request.user)
            if creds:
                service = gapi_build('calendar', 'v3', credentials=creds)
                event = _cita_to_google_event(cita)
                result = service.events().insert(calendarId='primary', body=event).execute()
                cita.google_event_id = result['id']
                cita.save(update_fields=['google_event_id'])
                google_synced = True
        except Exception as e:
            messages.warning(request, f'Cita guardada, pero no se pudo sincronizar con Google Calendar: {e}')

        from matriculas.models import Notificacion
        Notificacion.objects.create(
            usuario=request.user,
            tipo='cita',
            titulo=f'Nueva cita: {titulo}',
            mensaje=f'Cita programada para {cita.fecha_hora.strftime("%d/%m/%Y a las %H:%M")}',
            enlace='/calendario/'
        )

        if google_synced:
            messages.success(request, '✅ Cita agendada y sincronizada con Google Calendar.')
        else:
            messages.success(request, '✅ Cita agendada.')
        return redirect('calendario')
    else:
        initial = {}
        fecha = request.GET.get('fecha')
        if fecha:
            try:
                from datetime import datetime
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                initial['fecha_hora'] = fecha_dt.strftime('%Y-%m-%d')
            except:
                pass
        form = CitaForm(initial=initial if initial else None, psicologo=request.user)
    
    fecha_seleccionada = request.GET.get('fecha', '')
    es_fecha_fija = bool(fecha_seleccionada)
    
    profesores = User.objects.filter(perfil__rol='profesor').order_by('first_name', 'username')
    
    return render(request, 'matriculas/crear_cita.html', {'form': form, 'titulo': 'Nueva Cita', 'estudiantes': estudiantes, 'fecha_seleccionada': fecha_seleccionada, 'es_fecha_fija': es_fecha_fija, 'profesores': profesores, 'es_reunion_profesor': False})


@login_required
def editar_cita(request, pk):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    cita = get_object_or_404(Cita, pk=pk, psicologo=request.user)
    estudiantes = ProcesoPsicologico.objects.all().order_by('nombre_estudiante')
    
    if request.method == 'POST':
        tipo_cita = request.POST.get('tipo_cita', '')
        
        if tipo_cita:
            titulo = tipo_cita
        else:
            titulo = request.POST.get('titulo', 'Sin título')
        
        duracion = request.POST.get('duracion', '60')
        try:
            duracion = int(duracion)
        except:
            duracion = 60
        
        recordar = request.POST.get('recordar') == 'on'
        
        estudiante_id = request.POST.get('estudiante', '')
        if estudiante_id:
            try:
                cita.estudiante_id = int(estudiante_id)
            except:
                cita.estudiante = None
        else:
            cita.estudiante = None
        
        observaciones = request.POST.get('observaciones', '')
        
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
        
        if 'Reunión con' in tipo_cita:
            color = '#7d3c98'
        else:
            color = colores_tipo.get(tipo_cita, '#8b2be2')
        
        from datetime import datetime
        fecha = request.POST.get('fecha', '')
        hora = request.POST.get('hora', '09:00')
        
        if fecha and hora:
            try:
                fecha_hora_str = f"{fecha} {hora}"
                cita.fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
            except:
                pass
        elif fecha:
            try:
                cita.fecha_hora = datetime.strptime(fecha, '%Y-%m-%d')
            except:
                pass
        
        cita.tipo_cita = tipo_cita
        cita.titulo = titulo
        cita.duracion = duracion
        cita.color = color
        cita.observaciones = observaciones
        cita.recordar = recordar
        cita.save()
        
        messages.success(request, '✅ Cita actualizada.')
        return redirect('calendario')
    else:
        form = CitaForm(instance=cita, psicologo=request.user)
    
    profesores = User.objects.filter(perfil__rol='profesor').order_by('first_name', 'username')
    
    return render(request, 'matriculas/crear_cita.html', {'form': form, 'titulo': 'Editar Cita', 'editar': True, 'estudiantes': estudiantes, 'profesores': profesores, 'es_reunion_profesor': cita.tipo_cita and cita.tipo_cita.startswith('Reunión con'), 'profesor_seleccionado': cita.tipo_cita.replace('Reunión con ', '') if cita.tipo_cita and cita.tipo_cita.startswith('Reunión con') else ''})


@login_required
def eliminar_cita(request, pk):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    cita = get_object_or_404(Cita, pk=pk, psicologo=request.user)
    if request.method == 'POST':
        cita.delete()
        messages.success(request, '🗑️ Cita eliminada.')
        return redirect('calendario')
    return render(request, 'matriculas/confirmar_eliminar.html', {'objeto': cita, 'tipo': 'cita'})


@login_required
def eliminar_dia_no_habil(request, pk):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    dia = get_object_or_404(DiaNoHabil, pk=pk, psicologo=request.user)
    if request.method == 'POST':
        dia.delete()
        messages.success(request, '🗑️ Día no hábil eliminado.')
        return redirect('calendario')
    return render(request, 'matriculas/confirmar_eliminar.html', {'objeto': dia, 'tipo': 'dia_no_habil'})


@login_required
def api_citas(request):
    if not es_psicologo(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    citas = Cita.objects.filter(psicologo=request.user)
    data = []
    for c in citas:
        data.append({
            'id': c.pk,
            'titulo': c.titulo,
            'tipo': c.tipo_cita,
            'tipo_display': c.get_tipo_cita_display(),
            'color': c.color,
            'fecha_hora': c.fecha_hora.isoformat(),
            'duracion': c.duracion,
            'observaciones': c.observaciones,
        })
    return JsonResponse(data, safe=False)


@login_required
def config_tipos_cita(request):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        color = request.POST.get('color', '#8b2be2')
        
        if nombre:
            ConfigTipoCita.objects.create(
                psicologo=request.user,
                nombre=nombre,
                color=color
            )
            messages.success(request, '✅ Tipo de cita creado.')
        return redirect('calendario')
    
    return redirect('calendario')


@login_required
def eliminar_tipo_cita(request, pk):
    if not es_psicologo(request.user):
        return HttpResponseForbidden('Acceso denegado.')
    
    tipo = get_object_or_404(ConfigTipoCita, pk=pk, psicologo=request.user)
    tipo.delete()
    messages.success(request, '🗑️ Tipo de cita eliminado.')
    return redirect('calendario')


@login_required
def api_tipos_cita(request):
    if not es_psicologo(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        for item in data.get('tipos', []):
            ConfigTipoCita.objects.update_or_create(
                psicologo=request.user,
                nombre=item['nombre'],
                defaults={'color': item['color'], 'activo': item.get('activo', True)}
            )
        return JsonResponse({'ok': True})
    
    tipos = []
    for tc in ConfigTipoCita.objects.filter(psicologo=request.user, activo=True).order_by('orden', 'nombre'):
        tipos.append({'id': tc.pk, 'nombre': tc.nombre, 'color': tc.color, 'activo': tc.activo})
    
    return JsonResponse(tipos, safe=False)


@login_required
def marcar_notificacion_leida(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    notificacion.leida = True
    notificacion.save()
    return redirect(notificacion.enlace or '/')


# ══════════════════════════════════════════════════════════════════════
#  PANEL DE ADMINISTRACIÓN
# ══════════════════════════════════════════════════════════════════════
@login_required
def admin_dashboard(request):
    if not es_admin(request.user):
        return HttpResponseForbidden('Acceso denegado. Solo administradores.')

    total_usuarios    = User.objects.count()
    total_psicologos  = User.objects.filter(perfil__rol='psicologo').count()
    total_profesores  = User.objects.filter(perfil__rol='profesor').count()
    total_admins      = User.objects.filter(perfil__rol='admin').count()
    total_activos     = User.objects.filter(is_active=True).count()
    total_inactivos   = User.objects.filter(is_active=False).count()

    total_procesos        = ProcesoPsicologico.objects.count()
    procesos_activos      = ProcesoPsicologico.objects.filter(estado='activo').count()
    procesos_en_curso     = ProcesoPsicologico.objects.filter(estado='en_curso').count()
    procesos_finalizados  = ProcesoPsicologico.objects.filter(estado='finalizado').count()

    total_libros = Libro.objects.count()
    total_temas  = TemaForo.objects.count()
    total_citas  = Cita.objects.count()

    usuarios_recientes = User.objects.select_related('perfil').order_by('-date_joined')[:8]

    return render(request, 'matriculas/admin_dashboard.html', {
        'total_usuarios':    total_usuarios,
        'total_psicologos':  total_psicologos,
        'total_profesores':  total_profesores,
        'total_admins':      total_admins,
        'total_activos':     total_activos,
        'total_inactivos':   total_inactivos,
        'total_procesos':       total_procesos,
        'procesos_activos':     procesos_activos,
        'procesos_en_curso':    procesos_en_curso,
        'procesos_finalizados': procesos_finalizados,
        'total_libros':      total_libros,
        'total_temas':       total_temas,
        'total_citas':       total_citas,
        'usuarios_recientes': usuarios_recientes,
    })


@login_required
def admin_usuarios(request):
    if not es_admin(request.user):
        return HttpResponseForbidden('Acceso denegado. Solo administradores.')

    q          = request.GET.get('q', '')
    rol_filter = request.GET.get('rol', '')

    usuarios = User.objects.select_related('perfil').all()

    if q:
        usuarios = usuarios.filter(
            Q(first_name__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )
    if rol_filter:
        usuarios = usuarios.filter(perfil__rol=rol_filter)

    usuarios = usuarios.order_by('first_name', 'username')

    return render(request, 'matriculas/admin_usuarios.html', {
        'usuarios':   usuarios,
        'q':          q,
        'rol_filter': rol_filter,
        'roles':      PerfilUsuario.ROL_CHOICES,
    })


@login_required
def admin_crear_usuario(request):
    if not es_admin(request.user):
        return HttpResponseForbidden('Acceso denegado. Solo administradores.')

    form = AdminCrearUsuarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'✅ Usuario "{user.get_full_name() or user.username}" creado correctamente.')
        return redirect('admin_usuarios')

    return render(request, 'matriculas/admin_crear_usuario.html', {
        'form':   form,
        'titulo': 'Crear Nuevo Usuario',
    })


@login_required
def admin_editar_usuario(request, pk):
    if not es_admin(request.user):
        return HttpResponseForbidden('Acceso denegado. Solo administradores.')

    usuario = get_object_or_404(User, pk=pk)
    form    = AdminEditarUsuarioForm(request.POST or None, instance=usuario)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'✅ Usuario "{usuario.get_full_name() or usuario.username}" actualizado.')
        return redirect('admin_usuarios')

    return render(request, 'matriculas/admin_crear_usuario.html', {
        'form':    form,
        'titulo':  f'Editar Usuario: {usuario.get_full_name() or usuario.username}',
        'editar':  True,
        'usuario': usuario,
    })


@login_required
def admin_toggle_usuario(request, pk):
    if not es_admin(request.user):
        return HttpResponseForbidden('Acceso denegado. Solo administradores.')

    usuario = get_object_or_404(User, pk=pk)

    if usuario == request.user:
        messages.error(request, 'No puedes desactivar tu propio usuario.')
        return redirect('admin_usuarios')

    usuario.is_active = not usuario.is_active
    usuario.save()
    estado = 'activado' if usuario.is_active else 'desactivado'
    messages.success(request, f'✅ Usuario "{usuario.username}" {estado}.')
    return redirect('admin_usuarios')


@login_required
def admin_eliminar_usuario(request, pk):
    if not es_admin(request.user):
        return HttpResponseForbidden('Acceso denegado. Solo administradores.')

    usuario = get_object_or_404(User, pk=pk)

    if usuario == request.user:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('admin_usuarios')

    if request.method == 'POST':
        nombre = usuario.get_full_name() or usuario.username
        usuario.delete()
        messages.success(request, f'🗑️ Usuario "{nombre}" eliminado.')
        return redirect('admin_usuarios')

    return render(request, 'matriculas/confirmar_eliminar.html', {
        'objeto': usuario,
        'tipo':   'usuario',
    })
