"""Versiones inmutables de manuscritos Word."""
from datetime import datetime, timezone
from io import BytesIO
from hashlib import sha256
from docx import Document


def fecha():
    return datetime.now(timezone.utc).isoformat()


def validar_docx(contenido):
    if not contenido or not isinstance(contenido, bytes):
        raise ValueError('El archivo Word está vacío o es inválido.')
    Document(BytesIO(contenido))
    return contenido


def crear_version_original(nombre, contenido):
    if not nombre.lower().endswith('.docx'):
        raise ValueError('Se requiere un archivo .docx')
    validar_docx(contenido)
    return {'numero': 0, 'nombre': nombre, 'contenido': bytes(contenido),
            'fecha_utc': fecha(), 'tipo': 'Original', 'origen': 'autor',
            'sha256': sha256(contenido).hexdigest(), 'base': None}


def crear_version(base, contenido, origen, *, instrucciones=None):
    """Registra una nueva versión sin modificar los bytes de la anterior."""
    if origen not in ('autor_offline', 'astra'):
        raise ValueError('Origen no válido')
    validar_docx(contenido)
    numero = base['numero'] + 1
    return {'numero': numero, 'nombre': f'version_{numero}.docx',
            'contenido': bytes(contenido), 'fecha_utc': fecha(),
            'tipo': 'Edición offline' if origen == 'autor_offline' else 'Revisión Astra',
            'origen': origen, 'sha256': sha256(contenido).hexdigest(),
            'base': base['numero'], 'instrucciones': instrucciones or {}}


def crear_version_prueba(original, numero):
    """Compatibilidad histórica: no se usa para producir revisiones de IA."""
    if numero != original['numero'] + 1:
        raise ValueError('Número de versión no consecutivo')
    return crear_version(original, original['contenido'], 'autor_offline')


def crear_version_astra(base, cambios, instrucciones):
    """Prepara una versión verde desde cambios estructurados ya verificados.

    Cada cambio: {'original': str, 'nuevo': str}. Solo se admiten anclajes
    únicos contenidos en un run; ante ambigüedad no se genera la versión.
    La función no llama a Astra ni simula sus respuestas.
    """
    from copy import deepcopy
    from docx.enum.text import WD_COLOR_INDEX

    doc = Document(BytesIO(base['contenido']))
    def runs():
        for p in doc.paragraphs:
            yield from p.runs
        for tabla in doc.tables:
            for fila in tabla.rows:
                for celda in fila.cells:
                    for p in celda.paragraphs:
                        yield from p.runs
    # Validar todo antes de cambiar nada.
    ubicaciones = []
    for cambio in cambios:
        anterior, nuevo = cambio['original'], cambio['nuevo']
        if not anterior or not nuevo or anterior == nuevo:
            raise ValueError('Cambio vacío o idéntico')
        encontrados = [r for r in runs() if anterior in r.text]
        if len(encontrados) != 1:
            raise ValueError('El texto de origen no tiene un anclaje único dentro de un run')
        ubicaciones.append((encontrados[0], anterior, nuevo))
    if len({id(r) for r, _, _ in ubicaciones}) != len(ubicaciones):
        raise ValueError('Dos cambios comparten un run; dividir o revisar manualmente')
    for run, anterior, nuevo in ubicaciones:
        antes, despues = run.text.split(anterior, 1)
        run.text = antes
        insertado = run._parent.add_run(nuevo)
        if run._r.rPr is not None:
            insertado._r.insert(0, deepcopy(run._r.rPr))
        insertado.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
        run._r.addnext(insertado._r)
        if despues:
            final = run._parent.add_run(despues)
            if run._r.rPr is not None:
                final._r.insert(0, deepcopy(run._r.rPr))
            insertado._r.addnext(final._r)
    salida = BytesIO()
    doc.save(salida)
    return crear_version(base, salida.getvalue(), 'astra', instrucciones=instrucciones)
