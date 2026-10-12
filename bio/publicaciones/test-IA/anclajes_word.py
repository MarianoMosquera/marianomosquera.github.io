"""Anclajes deterministas de párrafos del cuerpo y celdas de tablas.

No se editan encabezados, pies, cuadros de texto, tablas anidadas ni otros
contenidos fuera de los bloques enumerados. La edición rechaza XML complejo.
"""
from io import BytesIO
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table


def recorrer_bloques(doc):
    numero_p = numero_t = 0
    for elemento in doc.element.body.iterchildren():
        if elemento.tag == qn('w:p'):
            numero_p += 1
            yield f'P{numero_p:04d}', Paragraph(elemento, doc)
        elif elemento.tag == qn('w:tbl'):
            numero_t += 1
            tabla = Table(elemento, doc)
            vistos = set()  # una celda combinada puede aparecer varias veces
            for ri, fila in enumerate(tabla.rows, 1):
                for ci, celda in enumerate(fila.cells, 1):
                    if id(celda._tc) in vistos:
                        continue
                    vistos.add(id(celda._tc))
                    for pi, parrafo in enumerate(celda.paragraphs, 1):
                        yield f'T{numero_t:04d}R{ri:04d}C{ci:04d}P{pi:04d}', parrafo


def obtener_bloques(contenido):
    doc = Document(BytesIO(contenido))
    return [{'id': identificador, 'texto': parrafo.text}
            for identificador, parrafo in recorrer_bloques(doc) if parrafo.text.strip()]


def texto_estructurado(contenido):
    """Una sola representación del texto: IDs + contenido, sin duplicación."""
    bloques = obtener_bloques(contenido)
    if not bloques:
        raise ValueError('El Word no contiene texto extraíble en bloques compatibles.')
    return '\n'.join(f"[{bloque['id']}] {bloque['texto']}" for bloque in bloques)
