"""Exportación auditada del manuscrito y sus versiones."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import json
from auditoria import manifestar


def crear_zip_auditoria(original, versiones, eventos, evaluacion=None, word_final=None):
    if not original:
        raise ValueError('Falta el manuscrito original')
    salida = BytesIO()
    with ZipFile(salida, 'w', ZIP_DEFLATED) as archivo:
        archivo.writestr('documentos/original.docx', original['contenido'])
        for version in versiones:
            archivo.writestr(f'documentos/version_{version["numero"]}.docx',
                             version['contenido'])
        if word_final is not None:
            archivo.writestr('documentos/final_atribuido.docx', word_final)
        archivo.writestr('auditoria/historial.json', json.dumps(
            manifestar(original, versiones, eventos, evaluacion),
            ensure_ascii=False, indent=2))
    return salida.getvalue()
