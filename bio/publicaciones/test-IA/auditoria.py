"""Manifest de trazabilidad verificable para TEST-IA (sin inferir autoría)."""
from datetime import datetime, timezone
from hashlib import sha256


def _resumen_version(version):
    return {k: v for k, v in version.items() if k != 'contenido'}


def validar_historial(original, versiones, eventos, evaluacion=None, word_final=None):
    if not original or original.get('numero') != 0:
        raise ValueError('Se requiere una versión original número 0')
    cadena = [original] + list(versiones)
    for n, version in enumerate(cadena):
        if version.get('numero') != n:
            raise ValueError(f'Numeración discontinua en versión {n}')
        if n and version.get('base') != n - 1:
            raise ValueError(f'Base incorrecta en versión {n}')
        contenido = version.get('contenido')
        if not isinstance(contenido, bytes) or sha256(contenido).hexdigest() != version.get('sha256'):
            raise ValueError(f'Integridad SHA-256 incorrecta en versión {n}')
    for evento in eventos:
        base = evento.get('base_version')
        if not isinstance(base, int) or base < 0 or base >= len(cadena):
            raise ValueError('Evento vinculado a versión inexistente')
        if evento.get('base_sha256') != cadena[base]['sha256']:
            raise ValueError('El hash de la base del evento no coincide')
        resultado = evento.get('version_resultante')
        if resultado is not None:
            if not isinstance(resultado, int) or resultado <= base or resultado >= len(cadena):
                raise ValueError('Versión resultante inexistente o anterior a su base')
            if evento.get('resultado_sha256') and evento['resultado_sha256'] != cadena[resultado]['sha256']:
                raise ValueError('El hash del resultado del evento no coincide')
    if word_final is not None and evaluacion is None:
        raise ValueError('No puede existir Word atribuido sin evaluación final')
    if evaluacion is not None and (not isinstance(evaluacion, dict) or not isinstance(evaluacion.get('contribuciones'), list)):
        raise ValueError('Evaluación final mal formada')
    if evaluacion is not None and 'sha256_evaluado' in evaluacion:
        vigente = cadena[-1]
        if evaluacion.get('sha256_evaluado') != vigente['sha256'] or evaluacion.get('version_evaluada') != vigente['numero']:
            raise ValueError('Evaluación desactualizada respecto del manuscrito vigente')
    if word_final is not None and evaluacion is not None and 'sha256_evaluado' in evaluacion:
        from cierre import validar_cierre_auditoria
        validar_cierre_auditoria(cadena[-1], evaluacion, word_final)
    return True


def manifestar(original, versiones, eventos, evaluacion=None, word_final=None):
    validar_historial(original, versiones, eventos, evaluacion, word_final)
    return {
        'esquema': 'TEST-IA-3',
        'generado_utc': datetime.now(timezone.utc).isoformat(),
        'estado': 'final_evaluado' if word_final is not None else 'provisional_sin_atribucion_final',
        'documento_original': original['nombre'],
        'original_sha256': original['sha256'],
        'version_vigente': (versiones[-1] if versiones else original)['numero'],
        'versiones': [_resumen_version(original)] + [_resumen_version(v) for v in versiones],
        'eventos': eventos,
        'evaluacion_final': evaluacion,
        'word_final_sha256': sha256(word_final).hexdigest() if word_final is not None else None,
        'criterio': ('Verde intermedio: modificaciones puntuales de Astra; traducción completa sin verde masivo. '
                     'Coherencia integral: admite informe verde al final. Verde final: atribución alta; '
                     'amarillo final: contribución parcial o incierta con estimación justificada. '
                     'Los porcentajes son estimaciones, no mediciones objetivas de autoría.'),
    }
