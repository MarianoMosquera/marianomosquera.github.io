"""TEST-IA: interfaz de versiones y trazabilidad, sin API conectada."""
import io
import streamlit as st
from docx import Document
from instrucciones import INSTRUCCIONES
from versiones import crear_version_original, crear_version
from iteraciones import crear_solicitud, registrar_carga_offline
from exportacion import crear_zip_auditoria

MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
st.set_page_config(page_title='TEST-IA', page_icon='🧪', layout='wide')
st.title('TEST-IA')
st.caption('Entorno de preparación y auditoría. La conexión con Astra está pendiente.')

st.subheader('1. Instrucciones')
archivo = st.file_uploader('Manuscrito original (.docx)', type=['docx'], key='original_upload')
if archivo is not None:
    contenido = archivo.getvalue()
    if st.session_state.get('original_firma') != (archivo.name, contenido):
        try:
            original_nuevo = crear_version_original(archivo.name, contenido)
        except Exception as exc:
            st.error(f'No se pudo leer el documento: {exc}')
            st.stop()
        st.session_state['original'] = original_nuevo
        st.session_state['versiones'] = []
        st.session_state['eventos'] = []
        st.session_state['evaluacion'] = None
        st.session_state['original_firma'] = (archivo.name, contenido)

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

categoria = st.selectbox('Categoría académica', list(INSTRUCCIONES))
st.write(INSTRUCCIONES[categoria]['descripcion'])
with st.expander('Prompt general que recibirá Astra'):
    st.write(INSTRUCCIONES[categoria]['prompt'])
especifica = st.text_area('Prompt específico del AUTOR', key='especifica', height=110)
alcance = st.radio('Alcance', ['Manuscrito completo', 'Fragmento'], horizontal=True)
ubicacion = st.text_input('Ubicación precisa (obligatoria para fragmentos)', key='ubicacion')
if st.button('Preparar solicitud para Astra', type='primary'):
    if not ultima:
        st.warning('Primero cargá el manuscrito.')
    else:
        try:
            solicitud = crear_solicitud(ultima, categoria,
                INSTRUCCIONES[categoria]['prompt'], especifica, alcance, ubicacion)
            st.session_state['eventos'].append(solicitud)
            st.success('Solicitud registrada. La ejecución con Astra aún no está habilitada.')
        except ValueError as exc:
            st.error(str(exc))

st.divider()
st.subheader('2. Versiones')
if not original:
    st.info('Cargá un manuscrito para consultar versiones.')
else:
    st.download_button('Descargar original', original['contenido'],
                       file_name=original['nombre'], mime=MIME)
    for version in versiones:
        st.download_button(f'Versión {version["numero"]} · {version["tipo"]}',
                           version['contenido'], file_name=version['nombre'],
                           mime=MIME, key=f'v_{version["numero"]}')
    if not versiones:
        st.caption('La Versión 1 de Astra se generará al conectar la API. No se crean versiones ficticias.')
    st.caption('Los cambios de Astra en las versiones de trabajo se resaltarán solo en verde.')

st.divider()
st.subheader('3. Iteraciones')
st.write('Podés descargar una versión, editarla fuera de TEST-IA y subir el Word editado como nueva versión vigente.')
if not original:
    st.info('Primero cargá el manuscrito original.')
else:
    subida = st.file_uploader('Subir Word editado offline (.docx)', type=['docx'],
                              key=f'offline_{ultima["numero"]}')
    if subida is not None and st.button('Incorporar como nueva versión vigente'):
        try:
            nuevo = crear_version(ultima, subida.getvalue(), 'autor_offline')
            if nuevo['sha256'] == ultima['sha256']:
                st.warning('El archivo es idéntico a la versión vigente; no se creó otra versión.')
            else:
                st.session_state['versiones'].append(nuevo)
                st.session_state['eventos'].append(registrar_carga_offline(ultima, nuevo))
                st.session_state['evaluacion'] = None
                st.rerun()
        except Exception as exc:
            st.error(f'No se incorporó el documento: {exc}')
    st.caption('Una carga offline no se atribuye automáticamente a Astra. Se conserva la versión anterior.')
    st.write(f'Eventos registrados: {len(eventos)}')
    with st.expander('Historial interno de iteraciones'):
        for evento in eventos:
            st.write(f'{evento["fecha_utc"]} · Base {evento["base_version"]} · '
                     f'{evento.get("tipo", evento.get("categoria", "Solicitud"))} · '
                     f'{evento.get("estado", "Registrado")}')

st.divider()
st.subheader('4. Tablero resumen')
evaluacion = st.session_state.get('evaluacion')
if evaluacion is None:
    st.info('Pendiente: Astra debe analizar la última versión y el historial completo para clasificar las contribuciones.')
    a, b = st.columns(2)
    a.metric('Verdes', '—')
    b.metric('Amarillas', '—')
else:
    a, b = st.columns(2)
    a.metric('Verdes', sum(c['color'] == 'verde' for c in evaluacion['contribuciones']))
    b.metric('Amarillas', sum(c['color'] == 'amarillo' for c in evaluacion['contribuciones']))
    st.caption('Porcentajes de IA: estimaciones, no mediciones objetivas de autoría.')

st.divider()
st.subheader('5. Descargas')
if not original:
    st.info('Cargá un documento para habilitar la auditoría.')
else:
    if evaluacion is None:
        st.info('Word final verde/amarillo pendiente de evaluación de Astra; no se fabricarán atribuciones.')
    zip_bytes = crear_zip_auditoria(original, versiones, eventos, evaluacion)
    st.download_button('Descargar ZIP de auditoría', zip_bytes,
                       file_name='TEST-IA_auditoria.zip', mime='application/zip')
