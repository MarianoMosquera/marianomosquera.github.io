"""Auditoría interna: no existe aceptación/rechazo por cambio."""
from datetime import datetime, timezone


def manifestar(original, versiones, eventos, evaluacion=None):
    return {'esquema': 'TEST-IA-2',
            'generado_utc': datetime.now(timezone.utc).isoformat(),
            'documento_original': original['nombre'],
            'original_sha256': original['sha256'],
            'versiones': [{k: v for k, v in version.items() if k != 'contenido'}
                         for version in versiones],
            'eventos': eventos,
            'evaluacion_final': evaluacion,
            'criterio': ('Los porcentajes de contribución son estimaciones de IA, '
                         'no probabilidades estadísticas ni mediciones objetivas.')}
