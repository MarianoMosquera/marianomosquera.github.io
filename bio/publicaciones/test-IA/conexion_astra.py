"""Conector explícito para TEST-IA. No persiste documentos, respuestas ni secretos.

El llamador conserva la respuesta íntegra en el expediente, y aplica cambios
solo después de validarlos. Sin credenciales no se realiza ninguna petición.
"""
import json
from io import BytesIO
from hashlib import sha256
from docx import Document
from protocolos import PROTOCOLO_ITERACION, PROTOCOLO_FINAL
from anclajes_word import texto_estructurado

MAX_DOCX_BYTES = 8 * 1024 * 1024
MAX_INPUT_CHARS = 125_000
MAX_OUTPUT_TOKENS = 32_000
DEFAULT_MODEL = 'gpt-6-astra'  # configurable en Streamlit Secrets

class ConexionErrorSegura(Exception):
    """Error que puede mostrarse al usuario sin revelar detalles del proveedor."""


def extraer_word(contenido):
    """Extrae párrafos y tablas en orden XML; no adjunta el binario al proveedor."""
    if not isinstance(contenido, bytes) or len(contenido) > MAX_DOCX_BYTES:
        raise ValueError('El Word excede el límite de 8 MB o es inválido.')
    try:
        doc = Document(BytesIO(contenido))
        from docx.oxml.ns import qn
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        lineas = []
        for bloque in doc.element.body.iterchildren():
            if bloque.tag == qn('w:p'):
                p = Paragraph(bloque, doc)
                if p.text.strip():
                    lineas.append(f'[PÁRRAFO] {p.text}')
            elif bloque.tag == qn('w:tbl'):
                t = Table(bloque, doc)
                lineas.append('[TABLA]')
                for fila in t.rows:
                    lineas.append(' | '.join(' / '.join(p.text for p in celda.paragraphs) for celda in fila.cells))
                lineas.append('[/TABLA]')
        texto = '\n'.join(lineas)
    except Exception as exc:
        raise ValueError('No se pudo extraer el contenido del Word.') from None
    if not texto.strip():
        raise ValueError('El Word no contiene texto extraíble.')
    return texto


def _limitar(texto):
    if len(texto) > MAX_INPUT_CHARS:
        raise ValueError('La solicitud supera el límite de contenido; no se enviará parcialmente.')
    return texto


def preparar_envio_revision(version, solicitud):
    if not isinstance(version['contenido'], bytes) or len(version['contenido']) > MAX_DOCX_BYTES:
        raise ValueError('El Word excede el límite de 8 MB o es inválido.')
    if version['sha256'] != sha256(version['contenido']).hexdigest():
        raise ValueError('La versión Word no supera la comprobación SHA-256.')
    if solicitud['base_version'] != version['numero'] or solicitud['base_sha256'] != version['sha256']:
        raise ValueError('La solicitud no corresponde a la versión vigente.')
    texto = texto_estructurado(version['contenido'])
    paquete = {
        'protocolo': PROTOCOLO_ITERACION,
        'categoria': solicitud['categoria'],
        'prompt_general': solicitud['instruccion_general'],
        'prompt_especifico': solicitud['instruccion_especifica'],
        'alcance': solicitud['alcance'], 'ubicacion': solicitud['ubicacion'],
        'version': version['numero'], 'sha256': version['sha256'],
        'contenido_word': texto,
        'formato_respuesta': {
            'cambios': [{'original': 'texto literal exacto dentro del bloque', 'nuevo': 'texto propuesto',
                         'motivo': 'justificación', 'ubicacion': 'ID exacto del contenido_word, ej. P0001'}],
            'informe': 'observaciones sin modificación',
        },
        'regla': ('Responder SOLO JSON válido con claves cambios (lista) e informe (texto). '
                  'No afirmar verificación bibliográfica externa: no hay herramientas web. '
                  'Usar exclusivamente los ID entre corchetes de contenido_word en ubicacion; el texto original '
                  'debe coincidir literalmente dentro de ese bloque, incluso si abarca varios runs. '
                  'Para cualquier categoría (Traducción, Corrección, Revisión bibliográfica, '
                  'Datos y resultados, Argumentación y Coherencia integral), cuando se soliciten '
                  'modificaciones del manuscrito, proponerlas en cambios con el ID del bloque. '
                  'Para reescribir un párrafo, usar su texto completo como original '
                  'y su texto completo revisado como nuevo. No omitir cambios del Word '
                  'trasladándolos al informe. Si la solicitud es solo analítica y no requiere '
                  'modificación textual, usar cambios=[] y documentar los hallazgos en informe; '
                  'si no se puede editar con seguridad, explicar la limitación en informe. '
                  'No inventar datos ni referencias.'),
    }
    return _limitar(json.dumps(paquete, ensure_ascii=False))


def preparar_envio_final(original, versiones, eventos):
    secuencia = [original] + list(versiones)
    if [v['numero'] for v in secuencia] != list(range(len(secuencia))):
        raise ValueError('Historial incompleto o no consecutivo.')
    for v in secuencia:
        if sha256(v['contenido']).hexdigest() != v['sha256']:
            raise ValueError('El historial contiene una versión alterada.')
    # No enviar campos redundantes ni binarios; sí los prompts y respuestas íntegros.
    historial = []
    for evento in eventos:
        entrada = {k: evento.get(k) for k in ('id', 'tipo', 'base_version', 'base_sha256',
                    'version_resultante', 'resultado_sha256', 'instruccion_general',
                    'instruccion_especifica', 'estado') if k in evento}
        if 'ejecucion' in evento:
            e = evento['ejecucion']
            entrada['ejecucion'] = {k: e.get(k) for k in ('modelo', 'estado', 'respuesta_completa', 'respuesta_sha256')}
        historial.append(entrada)
    paquete = {
        'protocolo': PROTOCOLO_FINAL,
        'versiones': [{'numero': v['numero'], 'sha256': v['sha256'],
                      'origen': v.get('origen'), 'texto': extraer_word(v['contenido'])} for v in secuencia],
        'eventos': historial,
        'formato_respuesta': {'versiones_examinadas': [v['numero'] for v in secuencia],
            'justificacion_global': 'justificación basada en historial',
            'contribuciones': [{'texto': 'fragmento literal del Word final', 'color': 'verde o amarillo',
                               'cuartil': 'Q1-Q4 solo si amarillo', 'justificacion': 'motivo',
                               'evidencias': [{'version': 0, 'detalle': 'hecho comprobable'}]}]},
        'regla': ('Responder SOLO JSON válido. No inventar atribuciones. '
                  'Anotar solo fragmentos inequívocos del Word final. '
                  'Si no hay evidencia suficiente, contribuciones=[]; '
                  'nunca dar porcentajes puntuales.'),
    }
    return _limitar(json.dumps(paquete, ensure_ascii=False))


def interpretar_json(texto):
    try:
        objeto = json.loads(texto)
    except (TypeError, json.JSONDecodeError):
        raise ValueError('La respuesta de Astra no es JSON válido.') from None
    if not isinstance(objeto, dict):
        raise ValueError('La respuesta de Astra debe ser un objeto JSON.')
    return objeto


def validar_cambios(respuesta):
    cambios = respuesta.get('cambios')
    if not isinstance(cambios, list) or len(cambios) > 150:
        raise ValueError('La lista de cambios es inválida o excesiva.')
    for cambio in cambios:
        if not isinstance(cambio, dict) or not all(isinstance(cambio.get(k), str) for k in ('original', 'nuevo', 'motivo', 'ubicacion')):
            raise ValueError('Un cambio carece de texto, motivo o ubicación.')
        if not cambio['original'].strip() or not cambio['nuevo'].strip() or not cambio['motivo'].strip():
            raise ValueError('Un cambio no está suficientemente documentado.')
    if not isinstance(respuesta.get('informe', ''), str):
        raise ValueError('El informe de Astra no es válido.')
    return cambios


def ejecutar_api(payload, *, api_key, model=DEFAULT_MODEL, client=None):
    """Único punto de salida a OpenAI. Nunca registra ni devuelve la API key."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise ConexionErrorSegura('Falta configurar OPENAI_API_KEY en Streamlit Secrets.')
    if not isinstance(model, str) or not model.strip():
        raise ConexionErrorSegura('Falta identificar el modelo.')
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=1800.0, max_retries=0)
    try:
        respuesta = client.responses.create(
            model=model, instructions='Sos un revisor académico. Devolvé exclusivamente JSON válido.',
            input=payload, max_output_tokens=MAX_OUTPUT_TOKENS,
            reasoning={"effort": "high"},
            store=False,
        )
        texto = respuesta.output_text
        if not isinstance(texto, str) or not texto.strip():
            raise ConexionErrorSegura('El modelo no devolvió contenido utilizable.')
        return texto
    except ConexionErrorSegura:
        raise
    except Exception:
        # No exponer mensajes del SDK, cabeceras, request body ni stacktrace.
        raise ConexionErrorSegura('Falló la llamada a OpenAI. Revisá la configuración o intentá nuevamente.') from None
