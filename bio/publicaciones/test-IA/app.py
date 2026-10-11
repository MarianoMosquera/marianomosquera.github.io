import io
import streamlit as st
from docx import Document

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
