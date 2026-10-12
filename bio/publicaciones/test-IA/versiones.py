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
    """Aplica sustituciones no solapadas por ID, de forma transaccional.

    Preserva el formato de cada tramo sin editar y el formato inicial del
    tramo reemplazado. Rechaza anclajes inválidos y XML complejo. No llama API.
    """
    from copy import deepcopy
    from docx.enum.text import WD_COLOR_INDEX
    from docx.oxml.ns import qn
    from docx.text.run import Run
    from anclajes_word import recorrer_bloques

    doc = Document(BytesIO(base['contenido']))
    bloques = dict(recorrer_bloques(doc))
    por_bloque = {}
    if not isinstance(cambios, list) or not cambios:
        raise ValueError('No hay cambios para aplicar')

    for cambio in cambios:
        anterior, nuevo = cambio['original'], cambio['nuevo']
        referencia = cambio.get('ubicacion')
        if referencia is None:
            coincidencias = [
                identificador
                for identificador, bloque in bloques.items()
                if anterior and bloque.text.count(anterior) == 1
            ]
            if len(coincidencias) != 1:
                raise ValueError('Cambio histórico sin anclaje único')
            referencia = coincidencias[0]
        elif not isinstance(referencia, str) or referencia not in bloques:
            raise ValueError('ID de bloque inexistente o no admitido')
        if not anterior or not nuevo or anterior == nuevo:
            raise ValueError('Cambio vacío o idéntico')
        parrafo = bloques[referencia]
        inicio = parrafo.text.find(anterior)
        if inicio < 0 or parrafo.text.find(anterior, inicio + 1) != -1:
            raise ValueError('El texto original no tiene un anclaje único en el bloque')
        por_bloque.setdefault(referencia, []).append((inicio, inicio + len(anterior), nuevo))

    # Prevalidar TODOS los bloques antes de modificar el documento en memoria.
    for identificador, operaciones in por_bloque.items():
        operaciones.sort(key=lambda x: (x[0], x[1]))
        if any(a[1] > b[0] for a, b in zip(operaciones, operaciones[1:])):
            raise ValueError('Los cambios se superponen en un mismo párrafo')
        parrafo = bloques[identificador]
        if any(hijo.tag not in (qn('w:pPr'), qn('w:r')) for hijo in parrafo._p.iterchildren()):
            raise ValueError('El párrafo contiene elementos Word complejos')
        if not parrafo.runs or ''.join(r.text for r in parrafo.runs) != parrafo.text:
            raise ValueError('El párrafo no es editable con seguridad')
        for run in parrafo.runs:
            if any(hijo.tag not in (qn('w:t'), qn('w:rPr'), qn('w:lastRenderedPageBreak')) for hijo in run._r.iterchildren()):
                raise ValueError('El párrafo contiene dibujos, campos, saltos u otros elementos')

    def copia_fragmento(run, texto):
        if not texto:
            return None
        elemento = deepcopy(run._r)
        nuevo_run = Run(elemento, run._parent)
        nuevo_run.text = texto
        return elemento

    resaltar = instrucciones.get('categoria') != 'Traducción'
    for identificador, operaciones in por_bloque.items():
        parrafo = bloques[identificador]
        originales = list(parrafo.runs)
        segmentos = []
        posicion = 0
        for run in originales:
            segmentos.append((run, posicion, posicion + len(run.text)))
            posicion += len(run.text)

        piezas = []
        def conservar(desde, hasta):
            for run, a, b in segmentos:
                inicio = max(desde, a)
                fin = min(hasta, b)
                if inicio < fin:
                    pieza = copia_fragmento(run, run.text[inicio-a:fin-a])
                    if pieza is not None:
                        piezas.append(pieza)

        cursor = 0
        for inicio, fin, nuevo in operaciones:
            conservar(cursor, inicio)
            primero = next((r for r, a, b in segmentos if a <= inicio < b), None)
            if primero is None:
                raise ValueError('No se encontró un run de origen')
            insertado = copia_fragmento(primero, nuevo)
            if insertado is None:
                raise ValueError('Sustitución inválida')
            if resaltar:
                Run(insertado, parrafo).font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
            piezas.append(insertado)
            cursor = fin
        conservar(cursor, posicion)
        for run in originales:
            parrafo._p.remove(run._r)
        for pieza in piezas:
            parrafo._p.append(pieza)

    salida = BytesIO()
    doc.save(salida)
    return crear_version(base, salida.getvalue(), 'astra', instrucciones=instrucciones)
