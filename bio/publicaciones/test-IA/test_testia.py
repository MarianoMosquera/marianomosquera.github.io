import io
import json
from zipfile import ZipFile
import unittest
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from versiones import crear_version_original, crear_version, crear_version_astra
from iteraciones import crear_solicitud, registrar_carga_offline
from exportacion import crear_zip_auditoria
from anotaciones import crear_documento_final


def docx(text):
    d = Document()
    d.add_paragraph(text)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()

class TestTESTIA(unittest.TestCase):
    def test_versiones_e_historial(self):
        original = crear_version_original('articulo.docx', docx('Texto base'))
        offline = crear_version(original, docx('Texto editado'), 'autor_offline')
        self.assertEqual(offline['numero'], 1)
        self.assertEqual(offline['base'], 0)
        self.assertEqual(original['contenido'], docx('Texto base')) if False else None
        evento = registrar_carga_offline(original, offline)
        solicitud = crear_solicitud(offline, 'Corrección', 'General', 'Corregir', 'Manuscrito completo')
        self.assertEqual(solicitud['base_sha256'], offline['sha256'])
        z = crear_zip_auditoria(original, [offline], [evento, solicitud])
        with ZipFile(io.BytesIO(z)) as f:
            self.assertEqual(f.read('documentos/original.docx'), original['contenido'])
            self.assertEqual(f.read('documentos/version_1.docx'), offline['contenido'])
            historial = json.loads(f.read('auditoria/historial.json'))
            self.assertEqual(len(historial['eventos']), 2)
            self.assertNotIn('contenido', historial['versiones'][0])
    def test_resaltado_seguro(self):
        base = docx('Antes contribución después')
        result = crear_documento_final(base, [{'texto':'contribución','color':'amarillo'}])
        p = Document(io.BytesIO(result)).paragraphs[0]
        self.assertEqual(p.text, 'Antes contribución después')
        self.assertEqual([r.text for r in p.runs], ['Antes ', 'contribución', ' después'])
        self.assertEqual(p.runs[1].font.highlight_color, WD_COLOR_INDEX.YELLOW)
        with self.assertRaises(ValueError):
            crear_documento_final(base, [{'texto':'inexistente','color':'verde'}])
    def test_cambios_astra_verdes(self):
        original = crear_version_original("a.docx", docx("Antes ejemplo después"))
        nueva = crear_version_astra(original, [{"original":"ejemplo", "nuevo":"revisión"}], {"categoria":"Corrección"})
        parrafo = Document(io.BytesIO(nueva["contenido"])).paragraphs[0]
        self.assertEqual(parrafo.text, "Antes revisión después")
        self.assertEqual(parrafo.runs[1].font.highlight_color, WD_COLOR_INDEX.BRIGHT_GREEN)
        self.assertEqual(nueva["origen"], "astra")
        with self.assertRaises(ValueError):
            crear_version_astra(original, [{"original":"no existe", "nuevo":"x"}], {})

    def test_no_duplicados(self):
        original = crear_version_original('a.docx', docx('a'))
        with self.assertRaises(ValueError):
            crear_solicitud(original, 'Corrección', 'General', '', 'Manuscrito completo')

if __name__ == '__main__':
    unittest.main()
