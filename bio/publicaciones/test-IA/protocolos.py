"""Protocolos verificables de TEST-IA. No realiza llamadas a la API."""
from hashlib import sha256

CUARTILES = {'Q1': '0–25 %', 'Q2': '>25–50 %', 'Q3': '>50–75 %', 'Q4': '>75–100 %'}

PROTOCOLO_ITERACION = '''PROTOCOLO OBLIGATORIO DE REVISIÓN EDITORIAL TEST-IA
Usa conjuntamente (1) el prompt general de la categoría, (2) el prompt específico del AUTOR y (3) la versión Word vigente. El específico concreta el encargo sin anular las restricciones del general. No inventes referencias, resultados ni afirmaciones.
Devuelve la propuesta completa y un registro estructurado de intervenciones con fragmento original, texto propuesto, localización, motivo y relación con la instrucción. Cada modificación editorial atribuible a Astra, incluso puntuación, se identificará mediante una anotación de sugerencia VERDE en la nueva versión Word. No pintes texto que no cambió. Si un anclaje es ambiguo, no lo modifiques silenciosamente: repórtalo.
Excepciones: en una traducción completa no resaltes masivamente el manuscrito; registra la traducción y su procedencia en el expediente. Para Coherencia integral se permite un informe de observaciones al final del Word, en verde, sin alterar el cuerpo.
Preserva formato y contenido ajeno a las intervenciones; no sobrescribas versiones. Registra la respuesta íntegra, la versión base, la versión resultante, el modelo, los parámetros, la fecha y las instrucciones exactas en el expediente de auditoría. No afirmes que el Word fue generado si el sistema no lo produjo y verificó.'''

PROTOCOLO_FINAL = '''PROTOCOLO OBLIGATORIO DE ATRIBUCIÓN FINAL TEST-IA
Evalúa la ÚLTIMA versión Word contra la versión 0 y TODAS las versiones intermedias, las respuestas completas de Astra y las ediciones offline del AUTOR, en orden cronológico. Reconstruye para cada fragmento candidato su aparición, transformación, aceptación, rechazo, reformulación o desaparición. Una coincidencia textual aislada NO prueba autoría.
Anota en VERDE únicamente contribuciones supervivientes de Astra con atribución total respaldada por evidencia histórica. Anota en AMARILLO únicamente contribuciones supervivientes de atribución incierta, asignando DIRECTAMENTE un cuartil Q1 (0–25 %), Q2 (>25–50 %), Q3 (>50–75 %) o Q4 (>75–100 %). NO calcules ni solicites porcentaje exacto. Los cuartiles se aplican SOLO al amarillo. Sin evidencia suficiente, no anotes.
Para cada anotación incluye texto exacto y localizable en el Word final, justificación específica y referencias a versiones/eventos que sustentan la decisión; para amarillo incluye además cuartil. No inventes evidencia, no atribuyas automáticamente traducción lingüística a autoría intelectual y no marques texto ausente del Word final. Devuelve evaluación estructurada, justificación global y constancia de las versiones efectivamente examinadas. El sistema debe rechazar anclajes ambiguos y evaluaciones que omitan versiones. El Word final solo agrega resaltados, sin cambiar su texto.'''


def preparar_iteracion(version, categoria, general, especifico, alcance='Manuscrito completo', ubicacion=''):
    if not general or not general.strip() or not especifico or not especifico.strip():
        raise ValueError('Se requieren los prompts general y específico completos')
    return {'protocolo': PROTOCOLO_ITERACION, 'categoria': categoria,
            'prompt_general': general, 'prompt_especifico': especifico,
            'alcance': alcance, 'ubicacion': ubicacion,
            'version_base': version['numero'], 'sha256_base': version['sha256'],
            'word_base_sha256': sha256(version['contenido']).hexdigest()}


def preparar_atribucion(original, versiones, eventos):
    secuencia = [original] + list(versiones)
    numeros = [v['numero'] for v in secuencia]
    if numeros != list(range(len(secuencia))):
        raise ValueError('El historial de versiones no es consecutivo y completo')
    if not eventos:
        raise ValueError('Falta el historial de intervenciones')
    return {'protocolo': PROTOCOLO_FINAL,
            'versiones': [{'numero': v['numero'], 'sha256': v['sha256'],
                           'tipo': v.get('tipo')} for v in secuencia],
            'eventos': eventos,
            'version_final': secuencia[-1]['numero'],
            'sha256_final': secuencia[-1]['sha256']}


def validar_trazabilidad_final(evaluacion, original, versiones):
    esperadas = [v['numero'] for v in [original] + list(versiones)]
    revisadas = evaluacion.get('versiones_examinadas')
    if revisadas != esperadas:
        raise ValueError('La evaluación final no acredita revisión de todas las versiones')
    for item in evaluacion.get('contribuciones', []):
        evidencias = item.get('evidencias')
        if not isinstance(evidencias, list) or not evidencias:
            raise ValueError('Faltan evidencias históricas de una contribución')
        for evidencia in evidencias:
            if not isinstance(evidencia, dict) or evidencia.get('version') not in esperadas or not evidencia.get('detalle'):
                raise ValueError('Evidencia histórica inválida')
    return True
