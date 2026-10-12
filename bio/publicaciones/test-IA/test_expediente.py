import io
import json
import unittest
from zipfile import ZipFile
from docx import Document
from versiones import crear_version_original, crear_version
from iteraciones import crear_solicitud, registrar_carga_offline
from expediente import registrar_respuesta, diagnosticar_expediente
from exportacion import crear_zip_auditoria


def word(texto):
    doc = Document(); doc.add_paragraph(texto)
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()


class TestExpediente(unittest.TestCase):
    def test_respuestas_prompts_y_versiones_completos(self):
        original = crear_version_original('original.docx', word('Texto'))
        nuevo = crear_version(original, word('Texto revisado'), 'astra')
        e = crear_solicitud(original, 'Corrección', 'GENERAL completo', 'ESPECÍFICO completo', 'Manuscrito completo')
        e = registrar_respuesta(e, 'RESPUESTA completa sin truncar', modelo='astra-prueba', parametros={'temperatura': 0})
        e['version_resultante'] = 1; e['resultado_sha256'] = nuevo['sha256']
        self.assertTrue(diagnosticar_expediente([e])['completo'])
        z = crear_zip_auditoria(original, [nuevo], [e], exigir_integridad=True)
        with ZipFile(io.BytesIO(z)) as f:
            self.assertIsNone(f.testzip())
            self.assertEqual(f.read('auditoria/interacciones/0001/prompt_general.txt').decode(), 'GENERAL completo')
            self.assertEqual(f.read('auditoria/interacciones/0001/prompt_especifico.txt').decode(), 'ESPECÍFICO completo')
            self.assertEqual(f.read('auditoria/interacciones/0001/respuesta_completa.txt').decode(), 'RESPUESTA completa sin truncar')
            self.assertTrue(json.loads(f.read('auditoria/estado_integridad.json'))['completo'])
            self.assertEqual(f.read('documentos/version_1.docx'), nuevo['contenido'])
    def test_no_declara_completo_si_falta_respuesta(self):
        original = crear_version_original('original.docx', word('Texto'))
        e = crear_solicitud(original, 'Corrección', 'General', 'Específico', 'Manuscrito completo')
        with self.assertRaisesRegex(ValueError, 'incompleto'):
            crear_zip_auditoria(original, [], [e], exigir_integridad=True)
        z = crear_zip_auditoria(original, [], [e])
        with ZipFile(io.BytesIO(z)) as f:
            self.assertFalse(json.loads(f.read('auditoria/estado_integridad.json'))['completo'])
    def test_no_sobrescribe_respuestas_y_registra_fallos(self):
        original = crear_version_original('original.docx', word('Texto'))
        e = crear_solicitud(original, 'Corrección', 'General', 'Específico', 'Manuscrito completo')
        fallo = registrar_respuesta(e, None, modelo='astra-prueba', estado='fallida', error='Timeout')
        self.assertTrue(diagnosticar_expediente([fallo])['completo'])
        with self.assertRaises(ValueError):
            registrar_respuesta(fallo, 'Otra respuesta', modelo='astra-prueba')
        self.assertNotIn('ejecucion', e)

if __name__ == '__main__': unittest.main()
