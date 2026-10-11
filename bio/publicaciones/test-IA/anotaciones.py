"""Aplicación estricta de resaltados finales sobre un DOCX existente.

Solo admite segmentos exactos y únicos dentro de un mismo run. Si no se puede
identificar con seguridad el segmento, se rechaza el cambio sin tocar el Word.
"""
from io import BytesIO
from copy import deepcopy
from docx import Document
from docx.enum.text import WD_COLOR_INDEX

COLORES = {'verde': WD_COLOR_INDEX.BRIGHT_GREEN,
           'amarillo': WD_COLOR_INDEX.YELLOW}


def _runs(documento):
    for p in documento.paragraphs:
        yield from p.runs
    for tabla in documento.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for p in celda.paragraphs:
                    yield from p.runs


def crear_documento_final(contenido, contribuciones):
    """Aplica resaltados sin añadir apéndices ni inventar atribuciones."""
    documento = Document(BytesIO(contenido))
    localizaciones = []
    for item in contribuciones:
        texto, color = item['texto'], item['color']
        if not texto or color not in COLORES:
            raise ValueError('Contribución o color inválido')
        encontrados = [(run, run.text.index(texto)) for run in _runs(documento)
                       if texto in run.text]
        if len(encontrados) != 1:
            raise ValueError(f'Anclaje no único o dividido entre runs: {texto[:60]!r}')
        localizaciones.append((encontrados[0][0], texto, color))
    # Para evitar offsets inestables, no se aceptan dos anclajes en el mismo run.
    if len({id(run) for run, _, _ in localizaciones}) != len(localizaciones):
        raise ValueError('Dos contribuciones comparten un run; se requiere revisión.')
    for run, texto, color in localizaciones:
        antes, despues = run.text.split(texto, 1)
        run.text = antes
        medio = run._parent.add_run(texto)
        if run._r.rPr is not None:
            medio._r.insert(0, deepcopy(run._r.rPr))
        medio.font.highlight_color = COLORES[color]
        run._r.addnext(medio._r)
        if despues:
            final = run._parent.add_run(despues)
            if run._r.rPr is not None:
                final._r.insert(0, deepcopy(run._r.rPr))
            medio._r.addnext(final._r)
    salida = BytesIO()
    documento.save(salida)
    return salida.getvalue()
