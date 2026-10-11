from iteraciones import (
    crear_intervencion,
    agregar_propuesta,
    decidir_propuesta,
    preparar_nueva_iteracion,
)
from anotaciones import crear_documento_anotado
from exportacion import crear_zip_auditoria
from versiones import crear_version_original, crear_version_prueba
from auditoria import crear_registro, registrar_decision
import io
import streamlit as st
from docx import Document
from instrucciones import INSTRUCCIONES

st.set_page_config(
    page_title="TEST-IA",
    page_icon="🧪",
    layout="wide"
)

st.title("TEST-IA")


archivo = st.file_uploader(
    "Cargar manuscrito Word",
    type=["docx"]
)

if archivo is not None:
    contenido = archivo.getvalue()
    documento = Document(io.BytesIO(contenido))

    st.success("Documento cargado correctamente")
    st.write("**Archivo:**", archivo.name)
    st.write("**Párrafos:**", len(documento.paragraphs))
    st.write("**Tablas:**", len(documento.tables))

    st.subheader("Vista preliminar del texto")

    texto = "\n\n".join(
        parrafo.text
        for parrafo in documento.paragraphs
        if parrafo.text.strip()
    )

    st.text_area(
        "Contenido extraído",
        value=texto,
        height=350
    )

    st.download_button(
        "Descargar Word original",
        data=contenido,
        file_name=archivo.name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


st.divider()
st.subheader("Instrucciones")

categoria = st.selectbox(
    "Seleccionar instrucción",
    options=list(INSTRUCCIONES.keys())
)

st.write(INSTRUCCIONES[categoria]["descripcion"])

instruccion_especifica = st.text_area(
    "Instrucción específica",
    placeholder="Escribí aquí qué necesitás que Astra haga con el manuscrito.",
    height=140,
    key=f"instruccion_{categoria}"
)

ubicacion_intervencion = st.text_input(
    "Ubicación en el manuscrito (opcional)",
    placeholder="Ej.: Introducción, párrafo 3; Tabla 2; Discusión",
    key=f"ubicacion_{categoria}",
)

with st.expander("Ver instrucción general"):
    st.write(INSTRUCCIONES[categoria]["prompt"])

if st.button("Preparar instrucción", type="primary"):
    if archivo is None:
        st.warning("Primero cargá un documento Word.")
    elif not instruccion_especifica.strip():
        st.warning("Escribí una instrucción específica.")
    else:
        registro = crear_registro(
            documento=archivo.name,
            categoria=categoria,
            instruccion_especifica=instruccion_especifica,
            instruccion_general=INSTRUCCIONES[categoria]["prompt"],
            ubicacion=ubicacion_intervencion.strip(),
        )
        if "auditoria" not in st.session_state:
            st.session_state["auditoria"] = []
        st.session_state["auditoria"].append(registro)
        st.success("Instrucción preparada y registrada correctamente.")
        st.write("**Categoría:**", categoria)
        st.write("**Documento:**", archivo.name)
        st.write("**Instrucción específica:**", instruccion_especifica)
        st.caption("Ejecución con Astra pendiente de conexión.")


st.divider()
st.subheader("Registro de auditoría")

registros = st.session_state.get("auditoria", [])

if not registros:
    st.info("Todavía no hay intervenciones registradas.")
else:
    st.write(f"Intervenciones registradas: {len(registros)}")

    for indice, registro in enumerate(registros):
        with st.expander(
            f'{indice + 1}. {registro["categoria"]} — '
            f'{registro["decision_autor"]}'
        ):
            st.write("**Documento:**", registro["documento"])
            st.write(
                "**Instrucción específica:**",
                registro["instruccion_especifica"]
            )
            st.write("**Fecha UTC:**", registro["fecha_utc"])

            decision = st.selectbox(
                "Decisión del autor",
                ["Pendiente", "Aceptada", "Rechazada", "Modificada"],
                index=[
                    "Pendiente", "Aceptada", "Rechazada", "Modificada"
                ].index(registro["decision_autor"]),
                key=f'decision_{registro["id"]}',
            )

            observaciones = st.text_area(
                "Observaciones del autor",
                value=registro["observaciones_autor"],
                key=f'observaciones_{registro["id"]}',
            )

            if st.button(
                "Guardar decisión",
                key=f'guardar_{registro["id"]}'
            ):
                st.session_state["auditoria"][indice] = registrar_decision(
                    registro, decision, observaciones
                )
                st.success("Decisión registrada.")
                st.rerun()


st.divider()
st.subheader("Versiones del manuscrito")

if archivo is None:
    st.info("Cargá un documento Word para gestionar sus versiones.")
else:
    contenido_actual = archivo.getvalue()

    if (
        "documento_original" not in st.session_state
        or st.session_state["documento_original"]["contenido"]
        != contenido_actual
    ):
        st.session_state["documento_original"] = (
            crear_version_original(archivo.name, contenido_actual)
        )
        st.session_state["versiones"] = []

    original = st.session_state["documento_original"]

    st.download_button(
        "Descargar manuscrito original",
        data=original["contenido"],
        file_name=original["nombre"],
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        key="descargar_original_test_ia",
    )

    if st.button("Crear versión de prueba"):
        numero = len(st.session_state["versiones"]) + 1
        nueva = crear_version_prueba(original, numero)
        st.session_state["versiones"].append(nueva)
        st.success(f"Versión {numero} creada.")

    for version in st.session_state["versiones"]:
        st.download_button(
            f'Descargar versión {version["numero"]}',
            data=version["contenido"],
            file_name=version["nombre"],
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key=f'descargar_version_{version["numero"]}',
        )


st.divider()
st.subheader("Descargas finales")

if archivo is None:
    st.info("Cargá un documento Word para habilitar las descargas.")
else:
    original = st.session_state.get("documento_original")
    versiones = st.session_state.get("versiones", [])
    registros = st.session_state.get("auditoria", [])

    if original is not None:
        anotado = crear_documento_anotado(original, registros)

        st.download_button(
            "Descargar documento anotado (.docx)",
            data=anotado,
            file_name="documento_anotado.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key="descargar_anotado_test_ia",
        )

        contenido_zip = crear_zip_auditoria(
            original,
            versiones,
            registros,
        )

        st.download_button(
            "Descargar auditoría (.zip)",
            data=contenido_zip,
            file_name="auditoria_test_ia.zip",
            mime="application/zip",
            key="descargar_zip_test_ia",
        )


st.divider()
st.subheader("Revisión iterativa de propuestas")

st.caption(
    "Modo de prueba: las propuestas son simuladas. "
    "Todavía no se realizan consultas a Astra."
)

alcance_iterativo = st.radio(
    "Alcance del análisis",
    ["Manuscrito completo", "Fragmento"],
    horizontal=True,
    key="alcance_iterativo",
)

if alcance_iterativo == "Fragmento":
    fragmento_iterativo = st.text_area(
        "Fragmento que se analizará",
        key="fragmento_iterativo",
        height=130,
    )
else:
    fragmento_iterativo = ""

if "intervenciones_iterativas" not in st.session_state:
    st.session_state["intervenciones_iterativas"] = []

if st.button("Crear propuesta de prueba", key="crear_propuesta_iterativa"):
    if archivo is None:
        st.warning("Primero cargá un documento Word.")
    elif not instruccion_especifica.strip():
        st.warning("Primero escribí una instrucción específica.")
    elif alcance_iterativo == "Fragmento" and not fragmento_iterativo.strip():
        st.warning("Indicá el fragmento que se analizará.")
    else:
        intervencion = crear_intervencion(
            categoria=categoria,
            instruccion=instruccion_especifica,
            alcance=alcance_iterativo,
            ubicacion=ubicacion_intervencion.strip(),
        )

        intervencion["documento"] = archivo.name
        intervencion["fragmento"] = fragmento_iterativo

        intervencion = agregar_propuesta(
            intervencion,
            "SIMULACIÓN: propuesta inicial para probar el circuito.",
            modelo="simulacion",
        )

        st.session_state["intervenciones_iterativas"].append(intervencion)
        st.rerun()

for indice, intervencion in enumerate(
    st.session_state["intervenciones_iterativas"]
):
    identificador = intervencion["id"]
    ultima = intervencion["iteraciones"][-1]

    with st.expander(
        f'Intervención {indice + 1} — '
        f'{intervencion["categoria"]} — {intervencion["estado"]}',
        expanded=True,
    ):
        st.write("**Alcance:**", intervencion["alcance"])
        st.write("**Ubicación:**", intervencion["ubicacion"])
        st.write("**Propuesta actual:**", ultima["propuesta"])

        st.write("**Historial de propuestas**")
        for paso in intervencion["iteraciones"]:
            st.write(
                f'Iteración {paso["numero"]}: '
                f'{paso["decision"]}'
            )
            st.write(paso["propuesta"])
            if paso["observaciones_autor"]:
                st.write(
                    "Instrucciones del autor:",
                    paso["observaciones_autor"],
                )

        if ultima["decision"] == "Pendiente":
            decision_iterativa = st.selectbox(
                "Decisión sobre esta propuesta",
                ["Aceptada", "Rechazada", "Modificar"],
                key=f"decision_iterativa_{identificador}_{ultima['numero']}",
            )

            observaciones_iterativas = st.text_area(
                "Instrucciones u observaciones del autor",
                key=f"observaciones_iterativas_{identificador}_{ultima['numero']}",
            )

            if st.button(
                "Guardar evaluación",
                key=f"evaluar_iterativa_{identificador}_{ultima['numero']}",
            ):
                try:
                    actualizado = decidir_propuesta(
                        intervencion,
                        decision_iterativa,
                        observaciones_iterativas,
                    )
                    st.session_state["intervenciones_iterativas"][indice] = (
                        actualizado
                    )
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        elif ultima["decision"] == "Modificar":
            st.info(
                "El autor solicitó una modificación. "
                "Puede generarse una nueva propuesta de prueba."
            )

            if st.button(
                "Generar nueva propuesta simulada",
                key=f"nueva_iterativa_{identificador}_{ultima['numero']}",
            ):
                solicitud = preparar_nueva_iteracion(intervencion)
                numero = len(intervencion["iteraciones"]) + 1

                propuesta = (
                    f"SIMULACIÓN: propuesta {numero}. "
                    "Instrucción recibida: "
                    f'{solicitud["instrucciones_autor"]}'
                )

                actualizado = agregar_propuesta(
                    intervencion,
                    propuesta,
                    modelo="simulacion",
                )

                st.session_state["intervenciones_iterativas"][indice] = (
                    actualizado
                )
                st.rerun()

        else:
            st.success(
                f'Intervención cerrada: {ultima["decision"]}.'
            )
