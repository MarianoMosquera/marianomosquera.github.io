"""Recuperación segura en memoria de expedientes TEST-IA, sin extraer archivos a disco."""
import io
import json
from hashlib import sha256
from zipfile import ZipFile, BadZipFile

from auditoria import validar_historial
from versiones import validar_docx

MAX_ZIP = 100 * 1024 * 1024
MAX_FILE = 60 * 1024 * 1024
MAX_TOTAL = 250 * 1024 * 1024
MAX_ENTRIES = 1500


def recuperar_zip_auditoria(datos):
    """Retorna el estado restaurable; no modifica la sesión si hay un error."""
    if not isinstance(datos, bytes) or not datos or len(datos) > MAX_ZIP:
        raise ValueError('ZIP vacío o demasiado grande (máximo 100 MB)')
    try:
        with ZipFile(io.BytesIO(datos)) as z:
            entradas = z.infolist()
            if len(entradas) > MAX_ENTRIES or sum(e.file_size for e in entradas) > MAX_TOTAL:
                raise ValueError('El ZIP excede los límites de seguridad')
            nombres = [e.filename for e in entradas]
            if len(nombres) != len(set(nombres)):
                raise ValueError('El ZIP contiene nombres duplicados')
            for e in entradas:
                if (e.file_size > MAX_FILE or e.is_dir() or e.filename.startswith('/')
                    or '\\' in e.filename or '..' in e.filename.split('/')
                    or e.flag_bits & 1 or ((e.external_attr >> 16) & 0o170000) == 0o120000):
                    raise ValueError('Entrada ZIP no admitida')
            if 'auditoria/historial.json' not in nombres or 'auditoria/inventario.json' not in nombres:
                raise ValueError('El ZIP no es un expediente TEST-IA compatible')
            def leer(ruta):
                info = z.getinfo(ruta)
                if info.file_size > MAX_FILE:
                    raise ValueError('Archivo interno demasiado grande')
                contenido = z.read(ruta)
                if len(contenido) != info.file_size:
                    raise ValueError('Longitud interna inválida')
                return contenido
            inventario = json.loads(leer('auditoria/inventario.json'))['archivos']
            rutas = [a['ruta'] for a in inventario]
            if len(rutas) != len(set(rutas)) or set(rutas) != set(nombres) - {'auditoria/inventario.json'}:
                raise ValueError('Inventario incompleto o inconsistente')
            for item in inventario:
                contenido = leer(item['ruta'])
                if len(contenido) != item['bytes'] or sha256(contenido).hexdigest() != item['sha256']:
                    raise ValueError('Hash SHA-256 del inventario incorrecto: ' + item['ruta'])
            manifiesto = json.loads(leer('auditoria/historial.json'))
            if manifiesto.get('esquema') != 'TEST-IA-3':
                raise ValueError('Esquema de expediente no compatible')
            metadatos = manifiesto.get('versiones')
            if not isinstance(metadatos, list) or not metadatos:
                raise ValueError('El expediente carece de versiones')
            cadena = []
            for i, metadato in enumerate(metadatos):
                ruta = 'documentos/original.docx' if i == 0 else f'documentos/version_{i}.docx'
                contenido = leer(ruta)
                validar_docx(contenido)
                version = dict(metadato)
                version['contenido'] = contenido
                cadena.append(version)
            eventos = manifiesto.get('eventos')
            if not isinstance(eventos, list):
                raise ValueError('Historial de eventos inválido')
            evaluacion = manifiesto.get('evaluacion_final')
            word_final = leer('documentos/final_atribuido.docx') if 'documentos/final_atribuido.docx' in nombres else None
            validar_historial(cadena[0], cadena[1:], eventos, evaluacion, word_final)
            if manifiesto.get('original_sha256') != cadena[0]['sha256']:
                raise ValueError('Hash del original no coincide')
            if manifiesto.get('version_vigente') != cadena[-1]['numero']:
                raise ValueError('Versión vigente inconsistente')
            if (word_final is None) != (manifiesto.get('word_final_sha256') is None):
                raise ValueError('Documento final inconsistente')
            if word_final is not None and sha256(word_final).hexdigest() != manifiesto['word_final_sha256']:
                raise ValueError('Hash del documento final incorrecto')
            # Un cierre final verificable puede reconstituirse desde el manifiesto
            # y el Word atribuido; una solicitud inconclusa NO se considera evaluada.
            cierre = None
            if word_final is not None and evaluacion is not None:
                vigente = cadena[-1]
                if (evaluacion.get('evaluador') == 'astra' and
                    evaluacion.get('version_evaluada') == vigente['numero'] and
                    evaluacion.get('sha256_evaluado') == vigente['sha256']):
                    cierre = {'estado': 'evaluacion_solicitada',
                              'version_final': vigente['numero'],
                              'sha256_final': vigente['sha256']}
            return {'original': cadena[0], 'versiones': cadena[1:], 'eventos': eventos,
                    'evaluacion_archivada': evaluacion, 'evaluacion': evaluacion if cierre else None,
                    'cierre': cierre}
    except (BadZipFile, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, IndexError) as exc:
        raise ValueError('ZIP de auditoría inválido o incompatible') from exc
