"""Configuración de las seis instrucciones de TEST-IA."""

INSTRUCCIONES = {
    "Traducción": {
        "descripcion": "Traducción académica fiel al texto original.",
        "prompt": (
            "Actúa como asistente de traducción académica. Traduce únicamente "
            "el contenido solicitado al idioma indicado, preservando sentido, "
            "estructura argumental, citas, nombres propios, referencias, datos, "
            "cifras y cautelas epistémicas. No añadas ideas, bibliografía ni "
            "resultados. Si un término admite traducciones sustantivamente "
            "distintas, señala la ambigüedad. Devuelve el texto propuesto y un "
            "registro localizable de cambios; distingue cualquier explicación "
            "de la traducción."
        ),
    },
    "Corrección": {
        "descripcion": "Corrección académica de estilo, lenguaje y terminología.",
        "prompt": (
            "Revisa ortografía, gramática, puntuación, terminología, fluidez "
            "y claridad académica del texto indicado. Conserva tesis, "
            "resultados, matices, referencias y significado. No inventes hechos "
            "ni amplíes el argumento salvo solicitud expresa. Devuelve una "
            "versión corregida y diferencias localizables; señala separadamente "
            "cambios que podrían afectar el sentido para aprobación del AUTOR."
        ),
    },
    "Revisión bibliográfica": {
        "descripcion": "Evaluación de citas, referencias y respaldo bibliográfico.",
        "prompt": (
            "Examina las referencias y las citas del manuscrito. Cuando existan "
            "herramientas de consulta disponibles, contrasta DOI, autores, "
            "título, año y publicación con Crossref, OpenAlex, PubMed, "
            "Semantic Scholar o editoriales, según pertinencia. Clasifica cada "
            "referencia como verificada, parcialmente verificada, no verificada "
            "o discrepante, indicando evidencia y fuente de comprobación. "
            "Verificar la existencia de una referencia NO prueba que respalde "
            "la afirmación citada: señala cuándo se requiere lectura de "
            "contenido. Nunca inventes fuentes ni DOI. Propón correcciones "
            "o referencias adicionales solo como sugerencias sujetas a "
            "aprobación del AUTOR; si no tienes acceso a fuentes externas, "
            "decláralo."
        ),
    },
    "Datos y resultados": {
        "descripcion": "Interpretación de datos y resultados ya existentes.",
        "prompt": (
            "Interpreta únicamente los datos, tablas, cifras y resultados ya "
            "reportados en el manuscrito, tomando sus cálculos como supuestos "
            "correctos a efectos de la tarea. Identifica tendencias, alcance "
            "interpretativo, incertidumbres y límites argumentativos. No "
            "ejecutes análisis estadísticos nuevos, no agregues bases externas, "
            "no modifiques cifras y no atribuyas a Astra cálculos que no "
            "realizó. Señala posibles inconsistencias únicamente como "
            "advertencias no verificadas; distingue observación, inferencia "
            "y sugerencia."
        ),
    },
    "Argumentación": {
        "descripcion": "Evaluación de tesis, premisas e inferencias.",
        "prompt": (
            "Analiza la estructura de la argumentación académica: tesis, "
            "premisas, inferencias, evidencia, objeciones, contraargumentos "
            "y conclusiones. Identifica debilidades y propone mejoras "
            "concretas con ubicación textual. No presentes como hechos "
            "nuevas afirmaciones no sustentadas. Distingue entre reformulación "
            "de ideas ya presentes y propuesta conceptual potencialmente "
            "nueva, que deberá contrastarse con el manuscrito original "
            "antes de atribuirla a IA."
        ),
    },
    "Coherencia integral": {
        "descripcion": "Evaluación global de la coherencia del manuscrito.",
        "prompt": (
            "Evalúa el manuscrito completo en términos de coherencia entre "
            "problema, objetivos, marco teórico, método, resultados, "
            "discusión, conclusiones y bibliografía. Detecta contradicciones, "
            "vacíos, desajustes y repeticiones; ofrece recomendaciones "
            "localizables y priorizadas. No inventes resultados ni cambies "
            "la tesis sin aprobación del AUTOR. Diferencia correcciones "
            "formales de cambios conceptuales y justifica cualquier aporte "
            "que parezca nuevo respecto del original."
        ),
    },
}
