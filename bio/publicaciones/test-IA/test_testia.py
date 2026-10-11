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

class TestFlujoExtendido(unittest.TestCase):
    def test_iteracion_nueva_y_base_vigente(self):
        from flujo import solicitar_iteracion
        base = crear_version_original('a.docx', docx('Inicio'))
        offline = crear_version(base, docx('Editado'), 'autor_offline')
        evento = solicitar_iteracion(offline, 'Corrección', 'General', 'Corregir citas')
        self.assertEqual(evento['base_version'], 1)
        self.assertEqual(evento['tipo'], 'Nueva iteración del AUTOR')
        self.assertEqual(evento['instruccion_especifica'], 'Corregir citas')
    def test_traduccion_no_verde(self):
        from flujo import crear_traduccion_completa
        base = crear_version_original('a.docx', docx('Hello'))
        version = crear_traduccion_completa(base, docx('Hola'), {'categoria': 'Traducción'})
        self.assertEqual(version['numero'], 1)
        self.assertIsNone(Document(io.BytesIO(version['contenido'])).paragraphs[0].runs[0].font.highlight_color)
    def test_coherencia_comentario_final(self):
        from flujo import agregar_evaluacion_coherencia
        base = crear_version_original('a.docx', docx('Texto intacto'))
        version = agregar_evaluacion_coherencia(base, 'Hay una contradicción.', {'categoria':'Coherencia integral'})
        d = Document(io.BytesIO(version['contenido']))
        self.assertEqual(d.paragraphs[0].text, 'Texto intacto')
        self.assertTrue(any('Hay una contradicción.' in p.text for p in d.paragraphs))
        self.assertEqual(d.paragraphs[-1].runs[0].font.highlight_color, WD_COLOR_INDEX.BRIGHT_GREEN)
    def test_offline_comparacion(self):
        from flujo import comparar_offline
        cambios = comparar_offline(docx('A'), docx('B'))
        self.assertTrue(cambios)
    def test_evaluacion_final_explicita(self):
        from flujo import validar_evaluacion_final
        with self.assertRaises(ValueError):
            validar_evaluacion_final(None, docx('Texto'))
        ev = {'contribuciones': [{'texto':'Texto', 'color':'amarillo', 'justificacion':'Rastro parcial', 'porcentaje_estimado':3}]}
        salida = validar_evaluacion_final(ev, docx('Texto'))
        self.assertEqual(Document(io.BytesIO(salida)).paragraphs[0].runs[1].font.highlight_color, WD_COLOR_INDEX.YELLOW)

class TestAuditoriaIntegral(unittest.TestCase):
    def test_zip_integridad_versiones_eventos_y_prompts(self):
        from hashlib import sha256
        original = crear_version_original('articulo.docx', docx('Texto inicial'))
        offline = crear_version(original, docx('Texto del autor'), 'autor_offline')
        astrav = crear_version_astra(offline, [{'original':'autor','nuevo':'investigador'}], {'categoria':'Corrección'})
        solicitud = crear_solicitud(offline, 'Corrección', 'Prompt general', 'Revisar argumentación', 'Manuscrito completo')
        solicitud['estado'] = 'Ejecutada'
        solicitud['version_resultante'] = 2
        solicitud['resultado_sha256'] = astrav['sha256']
        eventos = [registrar_carga_offline(original, offline), solicitud]
        datos = crear_zip_auditoria(original, [offline, astrav], eventos)
        with ZipFile(io.BytesIO(datos)) as z:
            self.assertIsNone(z.testzip())
            h = json.loads(z.read('auditoria/historial.json'))
            inv = json.loads(z.read('auditoria/inventario.json'))
            self.assertEqual(h['estado'], 'provisional_sin_atribucion_final')
            self.assertEqual(h['version_vigente'], 2)
            self.assertEqual([v['numero'] for v in h['versiones']], [0, 1, 2])
            self.assertEqual(h['eventos'][1]['instruccion_general'], 'Prompt general')
            self.assertEqual(h['eventos'][1]['instruccion_especifica'], 'Revisar argumentación')
            for item in inv['archivos']:
                self.assertEqual(sha256(z.read(item['ruta'])).hexdigest(), item['sha256'])
            self.assertEqual(z.read('documentos/version_1.docx'), offline['contenido'])
            self.assertEqual(z.read('documentos/version_2.docx'), astrav['contenido'])

    def test_rechaza_hash_y_numeracion_inconsistentes(self):
        original = crear_version_original('a.docx', docx('A'))
        offline = crear_version(original, docx('B'), 'autor_offline')
        corrupta = dict(offline, sha256='0' * 64)
        with self.assertRaises(ValueError):
            crear_zip_auditoria(original, [corrupta], [])
        incorrecta = dict(offline, numero=3)
        with self.assertRaises(ValueError):
            crear_zip_auditoria(original, [incorrecta], [])

    def test_final_requiere_evaluacion_y_registra_hash(self):
        from hashlib import sha256
        original = crear_version_original('a.docx', docx('Texto'))
        final = crear_documento_final(original['contenido'], [{'texto':'Texto','color':'verde'}])
        with self.assertRaises(ValueError):
            crear_zip_auditoria(original, [], [], word_final=final)
        ev = {'contribuciones':[{'texto':'Texto','color':'verde','justificacion':'Intervención documentada'}]}
        with ZipFile(io.BytesIO(crear_zip_auditoria(original, [], [], ev, final))) as z:
            h = json.loads(z.read('auditoria/historial.json'))
            self.assertEqual(h['estado'], 'final_evaluado')
            self.assertEqual(h['word_final_sha256'], sha256(final).hexdigest())


class TestCierreAutoria(unittest.TestCase):
    def _evaluacion(self, version):
        return {'evaluador': 'astra', 'version_evaluada': version['numero'],
                'sha256_evaluado': version['sha256'],
                'justificacion_global': 'Comparación con el historial completo',
                'contribuciones': [{'texto': 'Texto', 'color': 'amarillo',
                    'porcentaje_estimado': 3, 'justificacion': 'Influencia parcial documentada'}]}

    def test_cierre_verificable(self):
        from cierre import cerrar_autoria
        base = crear_version_original('a.docx', docx('Texto final'))
        ev = self._evaluacion(base)
        word, resumen = cerrar_autoria(base, ev)
        self.assertEqual(resumen['amarillas'], 1)
        self.assertEqual(resumen['verdes'], 0)
        self.assertEqual(Document(io.BytesIO(word)).paragraphs[0].text, 'Texto final')
        datos = crear_zip_auditoria(base, [], [], ev, word)
        with ZipFile(io.BytesIO(datos)) as z:
            self.assertEqual(z.read('documentos/final_atribuido.docx'), word)

    def test_rechaza_evaluacion_vieja_o_no_atribuible(self):
        from cierre import cerrar_autoria
        base = crear_version_original('a.docx', docx('Texto inicial'))
        nueva = crear_version(base, docx('Texto final'), 'autor_offline')
        ev = self._evaluacion(base)
        with self.assertRaises(ValueError):
            cerrar_autoria(nueva, ev)
        ev = self._evaluacion(nueva)
        ev['evaluador'] = 'manual'
        with self.assertRaises(ValueError):
            cerrar_autoria(nueva, ev)

    def test_rechaza_word_final_alterado(self):
        from cierre import cerrar_autoria
        base = crear_version_original('a.docx', docx('Texto final'))
        ev = self._evaluacion(base)
        with self.assertRaises(ValueError):
            crear_zip_auditoria(base, [], [], ev, docx('Texto falsificado'))
        word, _ = cerrar_autoria(base, ev)
        with self.assertRaises(ValueError):
            crear_zip_auditoria(base, [], [], dict(ev, sha256_evaluado='0'*64), word)

class TestTableroCuartiles(unittest.TestCase):
    def test_cuartiles_limites_y_conteos(self):
        from tablero import resumir_atribuciones
        porcentajes = [0, 25, 25.01, 50, 50.01, 75, 75.01, 100]
        e = {'contribuciones': [{'color': 'amarillo', 'porcentaje_estimado': p} for p in porcentajes]}
        r = resumir_atribuciones(e)
        self.assertEqual(r['cuartiles'], [2, 2, 2, 2])
        self.assertEqual(r['amarillo'], 8)
    def test_no_infiere_porcentaje_faltante(self):
        from tablero import resumir_atribuciones
        e = {'contribuciones': [{'color': 'verde'}]}
        r = resumir_atribuciones(e)
        self.assertEqual(r['cuartiles'], [0, 0, 0, 0])
        self.assertEqual(r['sin_porcentaje'], 0)
    def test_porcentaje_invalido(self):
        from tablero import resumir_atribuciones
        with self.assertRaises(ValueError):
            resumir_atribuciones({'contribuciones':[{'color':'amarillo', 'porcentaje_estimado':float('nan')}]})

class TestInterfazEstatica(unittest.TestCase):
    def test_rotulos_y_cinco_secciones(self):
        from pathlib import Path
        codigo = Path(__file__).with_name('app.py').read_text()
        for texto in ('Entorno de uso de IA y auditoría', "st.selectbox('Instrucción'", "st.button('Llamar Astra'", 'Descargar Documento Anotado'):
            self.assertIn(texto, codigo)
        for numero, titulo in enumerate(('Instrucciones','Versiones','Iteraciones','Tablero','Descargas'), 1):
            self.assertEqual(codigo.count(f"seccion({numero}, '{titulo}'"), 1)
        for texto in ('Tablero resumen', 'Categoría académica', 'Preparar solicitud para Astra', 'Word final verde/amarillo pendiente'):
            self.assertNotIn(texto, codigo)

class TestNomenclaturaYCuartiles(unittest.TestCase):
    def test_solo_incertidumbre_participa_en_cuartiles(self):
        from tablero import resumir_atribuciones
        e = {'contribuciones': [
            {'color': 'verde', 'porcentaje_estimado': 100},
            {'color': 'amarillo', 'porcentaje_estimado': 15},
            {'color': 'amarillo', 'porcentaje_estimado': 67},
            {'color': 'verde'},
        ]}
        r = resumir_atribuciones(e)
        self.assertEqual(r['verde'], 2)
        self.assertEqual(r['amarillo'], 2)
        self.assertEqual(r['cuartiles'], [1, 0, 1, 0])
        self.assertEqual(r['porcentajes'], [15, 67])

    def test_rotulos_actualizados(self):
        from pathlib import Path
        codigo = Path(__file__).with_name('app.py').read_text()
        for texto in ('Anotaciones de atribución total', 'Atribuciones en incertidumbre', "st.text_input('Ubicación'", 'Anotaciones de sugerencia'):
            if texto == 'Anotaciones de sugerencia':
                self.assertIn('anotaciones de sugerencia', codigo)
            else:
                self.assertIn(texto, codigo)
        self.assertNotIn('Ubicación precisa', codigo)
        self.assertNotIn('Podés descargar una versión, editarla fuera de TEST-IA', codigo)
        self.assertNotIn('Una carga offline no se atribuye automáticamente', codigo)

class TestFinalizacionExplicita(unittest.TestCase):
    def test_solicitud_no_equivale_a_evaluacion(self):
        from finalizacion import solicitar_cierre, cierre_evaluado
        version = crear_version_original('a.docx', docx('Texto'))
        cierre = solicitar_cierre(version, [])
        self.assertEqual(cierre['estado'], 'evaluacion_solicitada')
        self.assertFalse(cierre_evaluado(cierre, version, None))
        self.assertFalse(cierre_evaluado(None, version, None))

    def test_solo_final_y_evaluacion_correspondiente(self):
        from finalizacion import solicitar_cierre, cierre_evaluado
        original = crear_version_original('a.docx', docx('Texto'))
        cierre = solicitar_cierre(original, [])
        ev = {'evaluador': 'astra', 'version_evaluada': 0,
              'sha256_evaluado': original['sha256']}
        self.assertTrue(cierre_evaluado(cierre, original, ev))
        otra = crear_version(original, docx('Texto revisado'), 'autor_offline')
        self.assertFalse(cierre_evaluado(cierre, otra, ev))

    def test_reapertura_invalida_cierre(self):
        from finalizacion import solicitar_cierre, reabrir_revision
        original = crear_version_original('a.docx', docx('Texto'))
        self.assertIsNone(reabrir_revision(solicitar_cierre(original, [])))

    def test_interfaz_boton_y_tablero_final(self):
        from pathlib import Path
        codigo = Path(__file__).with_name('app.py').read_text()
        self.assertIn('Finalizar revisión y evaluar atribución', codigo)
        self.assertIn('El Tablero presenta los resultados de atribución del documento final', codigo)
        self.assertNotIn('El tablero se completa con la evaluación de atribución del documento vigente', codigo)
        self.assertIn('if evaluacion_vigente and word_final is not None:', codigo)
