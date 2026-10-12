"""ZIP de auditoría íntegro, sin resultados atribuidos ficticios."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
import json
from auditoria import manifestar
from expediente import diagnosticar_expediente


def crear_zip_auditoria(original, versiones, eventos, evaluacion=None, word_final=None, *, exigir_integridad=False):
    if not original:
        raise ValueError('Falta el manuscrito original')
    diagnostico = diagnosticar_expediente(eventos)
    if exigir_integridad and not diagnostico['completo']:
        raise ValueError('Expediente incompleto: ' + '; '.join(diagnostico['faltantes']))
    manifest = manifestar(original, versiones, eventos, evaluacion, word_final)
    manifest['integridad_expediente'] = diagnostico
    salida = BytesIO()
    with ZipFile(salida, 'w', ZIP_DEFLATED) as archivo:
        inventario = []
        def agregar(ruta, datos):
            archivo.writestr(ruta, datos)
            inventario.append({'ruta': ruta, 'sha256': sha256(datos).hexdigest(), 'bytes': len(datos)})
        agregar('documentos/original.docx', original['contenido'])
        for version in versiones:
            agregar(f'documentos/version_{version["numero"]}.docx', version['contenido'])
        if word_final is not None:
            agregar('documentos/final_atribuido.docx', word_final)
        for indice, evento in enumerate(eventos, 1):
            if 'instruccion_general' not in evento and 'instruccion_especifica' not in evento:
                continue
            carpeta = f'auditoria/interacciones/{indice:04d}'
            if 'instruccion_general' in evento:
                agregar(f'{carpeta}/prompt_general.txt', evento['instruccion_general'].encode('utf-8'))
            if 'instruccion_especifica' in evento:
                agregar(f'{carpeta}/prompt_especifico.txt', evento['instruccion_especifica'].encode('utf-8'))
            ejecucion = evento.get('ejecucion')
            if ejecucion:
                if ejecucion.get('respuesta_completa') is not None:
                    agregar(f'{carpeta}/respuesta_completa.txt', ejecucion['respuesta_completa'].encode('utf-8'))
                agregar(f'{carpeta}/ejecucion.json', json.dumps(ejecucion, ensure_ascii=False, indent=2).encode('utf-8'))
        agregar('auditoria/estado_integridad.json', json.dumps(diagnostico, ensure_ascii=False, indent=2).encode('utf-8'))
        agregar('auditoria/historial.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        agregar('auditoria/inventario.json', json.dumps({'archivos': inventario}, ensure_ascii=False, indent=2).encode('utf-8'))
    return salida.getvalue()
