"""Máquina de estados del cierre editorial de TEST-IA (sin llamada de red)."""
from datetime import datetime, timezone
from protocolos import PROTOCOLO_FINAL


def solicitar_cierre(version, eventos):
    if version is None:
        raise ValueError('No existe un manuscrito para finalizar')
    if not isinstance(eventos, list):
        raise ValueError('El historial de eventos es inválido')
    return {'estado': 'evaluacion_solicitada', 'protocolo_atribucion': PROTOCOLO_FINAL, 'version_final': version['numero'],
            'sha256_final': version['sha256'],
            'fecha_utc': datetime.now(timezone.utc).isoformat(),
            'eventos_al_cierre': len(eventos)}


def cierre_evaluado(cierre, version, evaluacion):
    return bool(cierre and cierre.get('estado') == 'evaluacion_solicitada'
                and version and cierre.get('version_final') == version['numero']
                and cierre.get('sha256_final') == version['sha256']
                and isinstance(evaluacion, dict)
                and evaluacion.get('evaluador') == 'astra'
                and evaluacion.get('version_evaluada') == version['numero']
                and evaluacion.get('sha256_evaluado') == version['sha256'])


def reabrir_revision(cierre):
    if not cierre:
        raise ValueError('No existe cierre para reabrir')
    return None
