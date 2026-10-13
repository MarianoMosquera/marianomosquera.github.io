"""Orquestación transaccional: la respuesta se registra aun si no se puede aplicar."""
from conexion_astra import (preparar_envio_revision, preparar_envio_final,
    interpretar_json, validar_cambios, ejecutar_api, ConexionErrorSegura, DEFAULT_MODEL)
from expediente import registrar_respuesta
from versiones import crear_version_astra
from flujo import agregar_evaluacion_coherencia
from protocolos import validar_trazabilidad_final
from cierre import cerrar_autoria


def procesar_revision(version, solicitud, *, api_key, model=DEFAULT_MODEL, cliente=None):
    payload = preparar_envio_revision(version, solicitud)
    try:
        texto = ejecutar_api(payload, api_key=api_key, model=model, client=cliente)
    except ConexionErrorSegura:
        fallida = registrar_respuesta(solicitud, None, modelo=model, estado='fallida',
                                     error='Error de conexión o respuesta vacía')
        return fallida, None, 'Falló la conexión; la solicitud quedó documentada.'
    evento = registrar_respuesta(solicitud, texto, modelo=model,
                                parametros={'store': False, 'max_output_tokens': 32000})
    try:
        respuesta = interpretar_json(texto)
        cambios = validar_cambios(respuesta)
        if cambios:
            nueva = crear_version_astra(version, cambios, {'categoria': solicitud['categoria'],
                                                              'id_solicitud': solicitud['id']})
        elif solicitud['categoria'] == 'Coherencia integral' and respuesta.get('informe', '').strip():
            nueva = agregar_evaluacion_coherencia(version, respuesta['informe'],
                                                  {'id_solicitud': solicitud['id']})
        else:
            nueva = None
        evento['version_resultante'] = nueva['numero'] if nueva else None
        evento['resultado_sha256'] = nueva['sha256'] if nueva else version['sha256']
        if not nueva:
            evento['nota_aplicacion'] = 'Respuesta registrada; sin cambios aplicables al Word.'
            return evento, None, ('Astra respondió, pero no propuso cambios aplicables al Word. '
                                  'Revisá el informe íntegro en el expediente; no se generó una versión.')
        return evento, nueva, None
    except (ValueError, KeyError, TypeError):
        evento['version_resultante'] = None
        evento['resultado_sha256'] = version['sha256']
        evento['nota_aplicacion'] = 'Respuesta íntegra registrada; cambios rechazados por validación.'
        return evento, None, 'Astra respondió, pero sus cambios no superaron la validación del Word. No se modificó el documento.'


def procesar_atribucion(original, versiones, eventos, *, api_key, model=DEFAULT_MODEL, cliente=None):
    payload = preparar_envio_final(original, versiones, eventos)
    texto = ejecutar_api(payload, api_key=api_key, model=model, client=cliente)
    objeto = interpretar_json(texto)
    objeto['evaluador'] = 'astra'
    ultima = versiones[-1] if versiones else original
    objeto['version_evaluada'] = ultima['numero']
    objeto['sha256_evaluado'] = ultima['sha256']
    validar_trazabilidad_final(objeto, original, versiones)
    cerrar_autoria(ultima, objeto)
    return objeto, texto
