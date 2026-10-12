import io
import json
import unittest
from zipfile import ZipFile, ZIP_DEFLATED
from docx import Document
from versiones import crear_version_original, crear_version
from iteraciones import crear_solicitud
from exportacion import crear_zip_auditoria
from recuperacion import recuperar_zip_auditoria


def word(t):
    d = Document(); d.add_paragraph(t); b = io.BytesIO(); d.save(b); return b.getvalue()


class TestRecuperacion(unittest.TestCase):
    def setUp(self):
        self.original = crear_version_original('manuscrito.docx', word('Original'))
        self.version = crear_version(self.original, word('Revisado'), 'autor_offline')
        self.evento = crear_solicitud(self.original, 'Corrección', 'General', 'Autor', 'Manuscrito completo')
        self.zip = crear_zip_auditoria(self.original, [self.version], [self.evento])

    def test_recuperar_paper_con_historial_y_bytes_identicos(self):
        r = recuperar_zip_auditoria(self.zip)
        self.assertEqual(r['original']['contenido'], self.original['contenido'])
        self.assertEqual(r['versiones'][0]['contenido'], self.version['contenido'])
        self.assertEqual(r['eventos'], [self.evento])
        self.assertIsNone(r['cierre'])
        self.assertIsNone(r['evaluacion'])
        siguiente = crear_version(r['versiones'][-1], word('Siguiente'), 'autor_offline')
        self.assertEqual(siguiente['numero'], 2)

    def test_recuperar_original_sin_iteraciones(self):
        z = crear_zip_auditoria(self.original, [], [])
        r = recuperar_zip_auditoria(z)
        self.assertEqual(r['versiones'], [])

    def test_rechazar_zip_modificado_aun_con_formato_valido(self):
        with ZipFile(io.BytesIO(self.zip)) as z:
            partes = {n: z.read(n) for n in z.namelist()}
        partes['documentos/original.docx'] = word('Manipulado')
        b = io.BytesIO()
        with ZipFile(b, 'w', ZIP_DEFLATED) as z:
            for n, contenido in partes.items(): z.writestr(n, contenido)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            recuperar_zip_auditoria(b.getvalue())

    def test_rechazar_zip_no_compatible(self):
        with self.assertRaises(ValueError): recuperar_zip_auditoria(b'basura')

    def test_rechazar_ruta_peligrosa(self):
        with ZipFile(io.BytesIO(self.zip)) as z:
            partes = {n: z.read(n) for n in z.namelist()}
        b = io.BytesIO()
        with ZipFile(b, 'w', ZIP_DEFLATED) as z:
            for n, contenido in partes.items(): z.writestr(n, contenido)
            z.writestr('../escape', b'x')
        with self.assertRaisesRegex(ValueError, 'no admitida'):
            recuperar_zip_auditoria(b.getvalue())

if __name__ == '__main__': unittest.main()
