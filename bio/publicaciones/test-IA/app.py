"""TEST-IA: interfaz de versiones y trazabilidad con conexión Astra opcional."""
import io
from hashlib import sha256
import streamlit as st
from docx import Document
from instrucciones import INSTRUCCIONES
from versiones import crear_version_original, crear_version
from iteraciones import crear_solicitud, registrar_carga_offline
from exportacion import crear_zip_auditoria
from flujo import solicitar_iteracion, comparar_offline, validar_evaluacion_final
from cierre import cerrar_autoria
from tablero import resumir_atribuciones
from finalizacion import solicitar_cierre, cierre_evaluado, reabrir_revision
from recuperacion import recuperar_zip_auditoria
from integracion import procesar_revision, procesar_atribucion
from conexion_astra import ConexionErrorSegura, DEFAULT_MODEL
from expediente import registrar_respuesta

MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
st.set_page_config(page_title='TEST-IA', page_icon='🧪', layout='wide')
st.title('TEST-IA')
st.caption('Entorno de uso de IA y auditoría')
# La credencial se obtiene del servicio de secretos, nunca de campos visibles.
def configuracion_astra():
    try:
        return str(st.secrets.get('OPENAI_API_KEY', '')), str(st.secrets.get('OPENAI_MODEL', DEFAULT_MODEL))
    except Exception:
        return '', DEFAULT_MODEL

api_key, modelo_astra = configuracion_astra()
st.caption('Astra: conexión configurada' if api_key else 'Astra: pendiente de configurar en Streamlit Secrets')
autorizacion = st.checkbox('Autorizo enviar el contenido del manuscrito a OpenAI para esta sesión.',
                           key='autorizar_envio_openai')

st.markdown("""<style>
.block-container {max-width: 1180px; padding-top: 2rem;}
h1 {letter-spacing: -.035em;}
.testia-section {padding: .85rem 1.1rem; margin: 1.6rem 0 .9rem; border-radius: 12px; border-left: 7px solid var(--accent); background: var(--bg);}
.testia-section h2 {font-size: 1.35rem; margin: 0; color: var(--text-color);}
.testia-section p {font-size: .88rem; margin: .3rem 0 0; color: var(--text-color); opacity: .8;}
</style>""", unsafe_allow_html=True)

def seccion(numero, titulo, descripcion, color, fondo):
    st.markdown(f'<div class="testia-section" style="--accent:{color};--bg:{fondo}"><h2>{numero}. {titulo}</h2><p>{descripcion}</p></div>', unsafe_allow_html=True)


# Gestión de expedientes: nunca se escriben manuscritos ni ZIP en el servidor.
# Los widgets de carga deben recrearse con claves nuevas al cambiar de paper.
def limpiar_paper():
    for clave in list(st.session_state):
        if clave != '_testia_paper_nonce':
            del st.session_state[clave]
    st.session_state['_testia_paper_nonce'] = st.session_state.get('_testia_paper_nonce', 0) + 1


nonce = st.session_state.get('_testia_paper_nonce', 0)
seccion(1, 'Instrucciones', 'Definí la intervención y el alcance sobre el manuscrito.', '#3566ad', 'rgba(53,102,173,.09)')
archivo = st.file_uploader('Manuscrito original (.docx)', type=['docx'], key=f'original_upload_{nonce}')
if archivo is not None:
    contenido = archivo.getvalue()
    if st.session_state.get('original_firma') != (archivo.name, contenido):
        try:
            original_nuevo = crear_version_original(archivo.name, contenido)
        except Exception as exc:
            st.error('No se pudo leer el documento Word.')
            st.stop()
        st.session_state['original'] = original_nuevo
        st.session_state['versiones'] = []
        st.session_state['eventos'] = []
        st.session_state['evaluacion'] = None
        st.session_state['cierre'] = None
        st.session_state['original_firma'] = (archivo.name, contenido)

cierre = st.session_state.get('cierre')
original = st.session_state.get('original')
versiones = st.session_state.get('versiones', [])
eventos = st.session_state.get('eventos', [])
ultima = versiones[-1] if versiones else original

if original:
    st.success(f'Manuscrito: {original["nombre"]} · Versión vigente: {ultima["numero"]}')
    with st.expander('Vista preliminar del documento'):
        doc = Document(io.BytesIO(ultima['contenido']))
        st.write(f'{len(doc.paragraphs)} párrafos · {len(doc.tables)} tablas')
        st.text_area('Texto de párrafos', '\n\n'.join(p.text for p in doc.paragraphs), height=220)

categoria = st.selectbox('Instrucción', list(INSTRUCCIONES))
st.write(INSTRUCCIONES[categoria]['descripcion'])
with st.expander('Prompt general que recibirá Astra'):
    st.write(INSTRUCCIONES[categoria]['prompt'])
especifica = st.text_area('Prompt específico del AUTOR', key=f'especifica_{nonce}', height=110)
alcance = st.radio('Alcance', ['Manuscrito completo', 'Fragmento'], horizontal=True)
ubicacion = st.text_input('Ubicación', key=f'ubicacion_{nonce}')
if st.button('Llamar Astra', type='primary'):
    if not ultima:
        st.warning('Primero cargá el manuscrito.')
    elif not autorizacion:
        st.warning('Debés autorizar expresamente el envío a OpenAI.')
    elif not api_key:
        st.warning('Configurá OPENAI_API_KEY en Streamlit Secrets antes de llamar a Astra.')
    else:
        try:
            solicitud = crear_solicitud(ultima, categoria,
                INSTRUCCIONES[categoria]['prompt'], especifica, alcance, ubicacion)
            with st.spinner('Procesando la revisión académica...'):
                evento, nueva, aviso = procesar_revision(ultima, solicitud, api_key=api_key, model=modelo_astra)
            st.session_state.setdefault('eventos', []).append(evento)
            if nueva is not None:
                st.session_state.setdefault('versiones', []).append(nueva)
            st.session_state['cierre'] = None
            st.session_state['evaluacion'] = None
            st.session_state['_testia_aviso'] = aviso or ('Nueva versión Astra registrada.' if nueva else 'Respuesta registrada; sin cambios en Word.')
            st.rerun()
        except ValueError:
            st.error('Solicitud inválida o documento demasiado grande. Revisá los datos y el archivo.')
        except Exception:
            st.error('No se completó la revisión. No se aplicaron cambios.')
if st.session_state.pop('_testia_aviso', None):
    st.info('Resultado de Astra registrado. Revisá las versiones y el expediente.')

st.divider()
seccion(2, 'Versiones', 'Consultá y descargá cada estado del documento.', '#16836b', 'rgba(22,131,107,.09)')
if not original:
    st.info('Cargá un manuscrito para consultar versiones.')
else:
    st.download_button('Descargar original', original['contenido'],
                       file_name=original['nombre'], mime=MIME)
    for version in versiones:
        st.download_button(f'Versión {version["numero"]} · {version["tipo"]}',
                           version['contenido'], file_name=version['nombre'],
                           mime=MIME, key=f'v_{nonce}_{version["numero"]}')
    st.caption('Las intervenciones editoriales de Astra se identifican mediante anotaciones de sugerencia.')
    st.caption('En traducciones completas no se resaltará todo el manuscrito. Las evaluaciones de coherencia integral pueden incorporarse como observaciones al final.')

st.divider()
seccion(3, 'Iteraciones', 'Continuá la revisión desde la versión vigente o incorporá una edición offline.', '#8d59b6', 'rgba(141,89,182,.09)')
if not original:
    st.info('Primero cargá el manuscrito original.')
else:
    if cierre:
        st.info('Revisión finalizada. Podés reabrirla para continuar con nuevas iteraciones.')
        if st.button('Reabrir revisión'):
            st.session_state['cierre'] = reabrir_revision(cierre)
            st.session_state['evaluacion'] = None
            st.rerun()
    if not cierre:
        st.markdown('**Edición offline y nuevas instrucciones**')
    subida = st.file_uploader('Subir Word editado offline (.docx)', type=['docx'],
                              key=f'offline_{nonce}_{ultima["numero"]}')
    if subida is not None and st.button('Incorporar como nueva versión vigente', disabled=bool(cierre)):
        try:
            nuevo = crear_version(ultima, subida.getvalue(), 'autor_offline')
            if nuevo['sha256'] == ultima['sha256']:
                st.warning('El archivo es idéntico a la versión vigente; no se creó otra versión.')
            else:
                st.session_state['versiones'].append(nuevo)
                evento = registrar_carga_offline(ultima, nuevo)
                evento['comparacion_parrafos'] = comparar_offline(ultima['contenido'], nuevo['contenido'])
                st.session_state['eventos'].append(evento)
                st.session_state['evaluacion'] = None
                st.rerun()
        except Exception as exc:
            st.error('No se incorporó el documento Word. Verificá el archivo.')
    st.markdown('**Solicitar nuevos cambios a Astra**')
    categoria_iter = st.selectbox('Instrucción de la nueva iteración', list(INSTRUCCIONES), key=f'categoria_iter_{nonce}')
    nuevas_instrucciones = st.text_area('Nuevos cambios solicitados por el AUTOR',
                                        height=180, key=f'nuevas_instrucciones_{nonce}',
                                        placeholder='Ej.: Reforzar el argumento del apartado 3 y revisar las citas.')
    alcance_iter = st.radio('Alcance de la nueva iteración',
                           ['Manuscrito completo', 'Fragmento'], horizontal=True, key=f'alcance_iter_{nonce}')
    ubicacion_iter = st.text_input('Ubicación del fragmento (si corresponde)', key=f'ubicacion_iter_{nonce}')
    if st.button('Llamar Astra · nueva iteración', disabled=bool(cierre)):
        if not autorizacion or not api_key:
            st.warning('Debés autorizar el envío y configurar la API key en Secrets.')
        else:
            try:
                solicitud = solicitar_iteracion(ultima, categoria_iter,
                    INSTRUCCIONES[categoria_iter]['prompt'], nuevas_instrucciones,
                    alcance_iter, ubicacion_iter)
                with st.spinner('Procesando la nueva iteración...'):
                    evento, nueva, aviso = procesar_revision(ultima, solicitud, api_key=api_key, model=modelo_astra)
                st.session_state['eventos'].append(evento)
                if nueva is not None:
                    st.session_state['versiones'].append(nueva)
                st.session_state['evaluacion'] = None
                st.session_state['_testia_aviso'] = aviso or 'Iteración registrada.'
                st.rerun()
            except ValueError:
                st.error('No se pudo validar la solicitud o el contenido Word.')
            except Exception:
                st.error('La iteración no pudo completarse. No se aplicaron cambios.')
    st.divider()
    if st.button('Finalizar revisión y evaluar atribución', type='primary', disabled=bool(cierre)):
        if not autorizacion or not api_key:
            st.warning('Para la atribución final debés autorizar el envío y configurar la API key.')
        else:
            try:
                with st.spinner('Evaluando el historial completo de versiones...'):
                    evaluacion_nueva, respuesta_final = procesar_atribucion(
                        original, st.session_state.get('versiones', []),
                        st.session_state.get('eventos', []), api_key=api_key, model=modelo_astra)
                st.session_state['evaluacion'] = evaluacion_nueva
                st.session_state['cierre'] = solicitar_cierre(ultima, st.session_state['eventos'])
                st.session_state['eventos'].append({
                    'tipo': 'Evaluación final de Astra', 'fecha_utc': st.session_state['cierre']['fecha_utc'],
                    'base_version': ultima['numero'], 'base_sha256': ultima['sha256'],
                    'estado': 'Evaluación final validada',
                    'respuesta_completa': respuesta_final,
                    'respuesta_sha256': sha256(respuesta_final.encode('utf-8')).hexdigest(),
                    'modelo': modelo_astra,
                })
                st.rerun()
            except (ValueError, ConexionErrorSegura):
                st.error('No fue posible validar la evaluación final. No se generó atribución.')
            except Exception:
                st.error('No se pudo completar la evaluación final. No se generó atribución.')
    st.write(f'Eventos registrados: {len(eventos)}')
    with st.expander('Historial interno de iteraciones'):
        for evento in eventos:
            st.write(f'{evento["fecha_utc"]} · Base {evento["base_version"]} · '
                     f'{evento.get("tipo", evento.get("categoria", "Solicitud"))} · '
                     f'{evento.get("estado", "Registrado")}')

st.divider()
seccion(4, 'Tablero', 'Distribución de contribuciones y estimaciones de atribución.', '#bd7728', 'rgba(189,119,40,.09)')
evaluacion = st.session_state.get('evaluacion')
evaluacion_vigente = cierre_evaluado(st.session_state.get('cierre'), ultima, evaluacion)
resumen = resumir_atribuciones(evaluacion if evaluacion_vigente else None)
a, b, c = st.columns(3)
a.metric('Anotaciones de atribución total', resumen['verde'] if evaluacion_vigente else '—')
b.metric('Atribuciones en incertidumbre', resumen['amarillo'] if evaluacion_vigente else '—')
c.metric('Total atribuido', resumen['total'] if evaluacion_vigente else '—')
st.markdown('**Atribuciones en incertidumbre · distribución por cuartiles**')
columnas = st.columns(4)
rotulos = ('Q1 · 0–25 %', 'Q2 · >25–50 %', 'Q3 · >50–75 %', 'Q4 · >75–100 %')
for columna, rotulo, cantidad in zip(columnas, rotulos, resumen['cuartiles']):
    columna.metric(rotulo, cantidad if evaluacion_vigente else '—')
if evaluacion_vigente:
    if resumen['sin_porcentaje']:
        st.caption(f'{resumen["sin_porcentaje"]} contribución(es) sin cuartil asignado.')
    st.caption('Los cuartiles se aplican exclusivamente a atribuciones en incertidumbre; expresan la clasificación por intervalo, sin porcentajes puntuales.')
else:
    st.caption('El Tablero presenta los resultados de atribución del documento final, una vez concluida la revisión.')

st.divider()
seccion(5, 'Descargas', 'Documento anotado y archivo completo de auditoría.', '#4a7894', 'rgba(74,120,148,.09)')
if not original:
    st.info('Cargá un documento para habilitar la auditoría.')
else:
    word_final = None
    if evaluacion_vigente:
        try:
            word_final, _ = cerrar_autoria(ultima, evaluacion)
            st.download_button('Descargar Documento Anotado', word_final,
                               file_name='TEST-IA_final.docx', mime=MIME)
        except ValueError as exc:
            st.error('Evaluación final inválida. No se generó el Word anotado.')
    try:
        zip_bytes = crear_zip_auditoria(
            original, versiones, eventos,
            evaluacion if evaluacion_vigente and word_final is not None else None,
            word_final if evaluacion_vigente else None)
        st.download_button('Descargar ZIP del paper (guardar o recuperar)', zip_bytes,
                           file_name='TEST-IA_auditoria.zip', mime='application/zip')
        if not evaluacion_vigente:
            st.caption('Expediente provisional: conserva versiones y eventos, sin atribución final validada.')
    except ValueError as exc:
        st.error('No se pudo preparar el expediente de auditoría.')


st.divider()
seccion(6, 'Gestión de papers', 'Iniciá una auditoría independiente o retomá un expediente guardado.', '#377b87', 'rgba(55,123,135,.09)')
st.markdown("""<style>
.testia-paper-card {padding: .7rem .1rem .35rem;}
.testia-paper-card h3 {font-size: 1.1rem; margin: 0 0 .4rem;}
.testia-paper-card p {font-size: .9rem; margin: 0 0 .6rem; opacity: .85;}
.testia-paper-new h3 {color: #198754;}
.testia-paper-restore h3 {color: #3978c6;}
</style>""", unsafe_allow_html=True)
col_nuevo, col_recuperar = st.columns(2, gap='large')
with col_nuevo:
    with st.container(border=True):
        st.markdown('<div class="testia-paper-card testia-paper-new"><h3>🟢 Nuevo paper</h3><p>Comenzá desde cero con un expediente independiente. Guardar el anterior es opcional.</p></div>', unsafe_allow_html=True)
        if st.button('Nuevo paper', key=f'nuevo_paper_{nonce}', use_container_width=True):
            st.session_state['_testia_confirmar_nuevo'] = True
        if st.session_state.get('_testia_confirmar_nuevo'):
            st.warning('Si no descargaste el expediente, perderás el trabajo de este paper al abandonarlo.')
            if st.button('Abandonar y comenzar nuevo paper', key=f'confirmar_nuevo_{nonce}', use_container_width=True):
                limpiar_paper()
                st.rerun()
            if st.button('Cancelar', key=f'cancelar_nuevo_{nonce}', use_container_width=True):
                st.session_state['_testia_confirmar_nuevo'] = False
                st.rerun()
with col_recuperar:
    with st.container(border=True):
        st.markdown('<div class="testia-paper-card testia-paper-restore"><h3>🔵 Recuperar paper</h3><p>Subí un ZIP de TEST-IA para retomar versiones, eventos y evidencias de una auditoría anterior.</p></div>', unsafe_allow_html=True)
        zip_subido = st.file_uploader('Expediente ZIP de TEST-IA', type=['zip'],
                                      key=f'recuperar_zip_{nonce}')
        if zip_subido is not None:
            st.caption('La recuperación reemplaza el paper actual. No se envía el ZIP a GitHub.')
            if st.button('Verificar y recuperar paper', key=f'confirmar_recuperar_{nonce}', use_container_width=True):
                try:
                    recuperado = recuperar_zip_auditoria(zip_subido.getvalue())
                except ValueError as exc:
                    st.error('No se recuperó el expediente: archivo inválido o incompatible.')
                else:
                    limpiar_paper()
                    st.session_state.update(recuperado)
                    st.session_state['original_firma'] = None
                    st.session_state['_testia_recuperado'] = True
                    st.rerun()
if st.session_state.pop('_testia_recuperado', False):
    st.success('Paper recuperado: versiones y eventos restaurados; la atribución final se muestra únicamente si estaba validada en el expediente.')
