"""Exportación de documentos y auditoría de TEST-IA."""

import json
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED


def crear_zip_auditoria(original, versiones, registros):
    """Construye un ZIP descargable sin escribir archivos en disco."""
    salida = BytesIO()

    with ZipFile(salida, "w", ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "documentos/original.docx",
            original["contenido"],
        )

        for version in versiones:
            zip_file.writestr(
                f'documentos/version_{version["numero"]}.docx',
                version["contenido"],
            )

        zip_file.writestr(
            "auditoria/registro.json",
            json.dumps(
                registros,
                ensure_ascii=False,
                indent=2,
            ),
        )

    return salida.getvalue()
