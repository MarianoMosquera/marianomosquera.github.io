"""ZIP de auditoría íntegro, sin resultados atribuidos ficticios."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
import json
from auditoria import manifestar


def crear_zip_auditoria(original, versiones, eventos, evaluacion=None, word_final=None):
    if not original:
        raise ValueError('Falta el manuscrito original')
    manifest = manifestar(original, versiones, eventos, evaluacion, word_final)
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
        agregar('auditoria/historial.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        agregar('auditoria/inventario.json', json.dumps({'archivos': inventario}, ensure_ascii=False, indent=2).encode('utf-8'))
    return salida.getvalue()
