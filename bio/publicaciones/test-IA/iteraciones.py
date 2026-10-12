"""Historial de solicitudes, cambios offline y evaluaciones finales."""
from datetime import datetime, timezone
from uuid import uuid4
from protocolos import preparar_iteracion


def fecha_actual():
    return datetime.now(timezone.utc).isoformat()


def crear_solicitud(base, categoria, general, especifica, alcance, ubicacion=''):
    if not especifica.strip():
        raise ValueError('Escribí una instrucción específica.')
    if alcance not in ('Manuscrito completo', 'Fragmento'):
        raise ValueError('Alcance inválido.')
    if alcance == 'Fragmento' and not ubicacion.strip():
        raise ValueError('Indicá una ubicación precisa para el fragmento.')
    protocolo = preparar_iteracion(base, categoria, general, especifica, alcance, ubicacion)
    return {'id': str(uuid4()), 'fecha_utc': fecha_actual(),
            'protocolo_revision': protocolo,
            'base_version': base['numero'], 'base_sha256': base['sha256'],
            'categoria': categoria, 'instruccion_general': general,
            'instruccion_especifica': especifica, 'alcance': alcance,
            'ubicacion': ubicacion, 'estado': 'Pendiente de Astra',
            'version_resultante': None}


def registrar_carga_offline(base, version):
    return {'id': str(uuid4()), 'fecha_utc': fecha_actual(),
            'tipo': 'Carga offline del AUTOR', 'base_version': base['numero'],
            'base_sha256': base['sha256'], 'version_resultante': version['numero'],
            'resultado_sha256': version['sha256'],
            'nota': 'El Word del AUTOR sustituye la base vigente; se conserva el historial.'}
