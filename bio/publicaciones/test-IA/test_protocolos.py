import io
import unittest
from docx import Document
from protocolos import (preparar_iteracion, preparar_atribucion,
                        validar_trazabilidad_final, CUARTILES)
from flujo import validar_evaluacion_final
from tablero import resumir_atribuciones
from versiones import crear_version_original, crear_version


def word(texto):
    doc = Document()
    doc.add_paragraph(texto)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestProtocolos(unittest.TestCase):
    def test_iteracion_incluye_ambos_prompts_y_word(self):
        base = crear_version_original('a.docx', word('Texto'))
        salida = preparar_iteracion(base, 'Corrección', 'GENERAL', 'ESPECIFICO')
        self.assertEqual(salida['prompt_general'], 'GENERAL')
        self.assertEqual(salida['prompt_especifico'], 'ESPECIFICO')
        self.assertEqual(salida['version_base'], 0)
        self.assertIn('VERDE', salida['protocolo'])

    def test_protocolo_final_exige_historial_completo(self):
        base = crear_version_original('a.docx', word('A'))
        v1 = crear_version(base, word('B'), 'autor_offline')
        paquete = preparar_atribucion(base, [v1], [{'tipo': 'Edición offline'}])
        self.assertEqual([v['numero'] for v in paquete['versiones']], [0, 1])
        self.assertIn('NO calcules ni solicites porcentaje exacto', paquete['protocolo'])
        ev = {'versiones_examinadas': [0, 1], 'contribuciones': [
            {'evidencias': [{'version': 0, 'detalle': 'Original'}, {'version': 1, 'detalle': 'Revisión'}]}]}
        self.assertTrue(validar_trazabilidad_final(ev, base, [v1]))
        ev['versiones_examinadas'] = [1]
        with self.assertRaises(ValueError):
            validar_trazabilidad_final(ev, base, [v1])

    def test_amarillo_con_cuartil_sin_porcentaje(self):
        ev = {'contribuciones': [{'texto': 'Texto', 'color': 'amarillo',
               'cuartil': 'Q3', 'justificacion': 'Influencia parcial'}]}
        salida = validar_evaluacion_final(ev, word('Texto'))
        self.assertTrue(salida)
        resumen = resumir_atribuciones(ev)
        self.assertEqual(resumen['cuartiles'], [0, 0, 1, 0])
        self.assertEqual(resumen['sin_porcentaje'], 0)

    def test_cuartil_invalido_rechazado(self):
        ev = {'contribuciones': [{'texto': 'Texto', 'color': 'amarillo',
               'cuartil': 'Q5', 'justificacion': 'x'}]}
        with self.assertRaises(ValueError):
            validar_evaluacion_final(ev, word('Texto'))
        self.assertEqual(len(CUARTILES), 4)

if __name__ == '__main__':
    unittest.main()
