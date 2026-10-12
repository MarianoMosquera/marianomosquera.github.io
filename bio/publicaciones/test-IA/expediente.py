"""Expediente íntegro de solicitudes y respuestas, sin conexión externa."""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4


def registrar_respuesta(evento, respuesta, *, modelo, parametros=None, estado='completada', error=None):
    """Devuelve un evento nuevo con evidencia textual íntegra; nunca modifica el original."""
    if not isinstance(evento, dict) or not evento.get('id'):
        raise ValueError('Solicitud sin identificador')
    if not evento.get('instruccion_general') or not evento.get('instruccion_especifica'):
        raise ValueError('La solicitud carece de prompts íntegros')
    if estado not in ('completada', 'fallida'):
        raise ValueError('Estado de ejecución inválido')
    if not isinstance(modelo, str) or not modelo.strip():
        raise ValueError('Modelo no identificado')
    if estado == 'completada' and (not isinstance(respuesta, str) or not respuesta.strip()):
        raise ValueError('La respuesta completa es obligatoria')
    if estado == 'fallida' and not error:
        raise ValueError('Las llamadas fallidas requieren detalle de error')
    if parametros is not None and not isinstance(parametros, dict):
        raise ValueError('Parámetros inválidos')
    if 'ejecucion' in evento:
        raise ValueError('No se puede sobrescribir una ejecución registrada')
    copia = dict(evento)
    copia['ejecucion'] = {
        'id': str(uuid4()), 'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'estado': estado, 'modelo': modelo, 'parametros': dict(parametros or {}),
        'respuesta_completa': respuesta if isinstance(respuesta, str) else None,
        'respuesta_sha256': sha256(respuesta.encode('utf-8')).hexdigest() if isinstance(respuesta, str) else None,
        'error': error,
    }
    copia['estado'] = 'Ejecutada' if estado == 'completada' else 'Fallida'
    return copia


def diagnosticar_expediente(eventos):
    """Lista omisiones sin inventar respuestas ni marcar el expediente como completo."""
    faltantes = []
    ids = set()
    for i, e in enumerate(eventos, 1):
        identificador = e.get('id')
        if identificador:
            if identificador in ids:
                faltantes.append(f'Evento {i}: identificador duplicado')
            ids.add(identificador)
        es_llamada = 'instruccion_general' in e or 'instruccion_especifica' in e
        if not es_llamada:
            continue
        for campo in ('id', 'instruccion_general', 'instruccion_especifica'):
            if not e.get(campo):
                faltantes.append(f'Evento {i}: falta {campo}')
        ejecucion = e.get('ejecucion')
        if not ejecucion:
            faltantes.append(f'Evento {i}: respuesta de Astra no registrada')
            continue
        if ejecucion.get('estado') == 'completada':
            respuesta = ejecucion.get('respuesta_completa')
            if not isinstance(respuesta, str) or not respuesta.strip():
                faltantes.append(f'Evento {i}: respuesta completa ausente')
            elif sha256(respuesta.encode('utf-8')).hexdigest() != ejecucion.get('respuesta_sha256'):
                faltantes.append(f'Evento {i}: hash de respuesta inválido')
            if e.get('version_resultante') is None:
                faltantes.append(f'Evento {i}: versión resultante sin registrar')
        elif ejecucion.get('estado') == 'fallida':
            if not ejecucion.get('error'):
                faltantes.append(f'Evento {i}: error no documentado')
        else:
            faltantes.append(f'Evento {i}: estado de ejecución inválido')
        if not ejecucion.get('modelo') or not ejecucion.get('fecha_utc'):
            faltantes.append(f'Evento {i}: modelo o fecha faltante')
    return {'completo': not faltantes, 'faltantes': faltantes,
            'llamadas_registradas': sum('instruccion_general' in e for e in eventos)}
