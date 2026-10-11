# Desarrollo de orquestador para auditoría en uso de IA

## 1. Propósito y perfiles

El sistema registra el uso de un AUTOR de Astra en manuscritos académicos y entrega al EDITOR evidencia verificable de instrucciones, respuestas, iteraciones, cambios humanos y contribuciones de IA conservadas en el Paper Final (PF). La integridad del registro no demuestra que se haya declarado toda la IA usada fuera del sistema, antes o durante el proceso [E1–E5].

| AUTOR | EDITOR |
|---|---|
| Trabaja sobre un Paper ID, ejecuta instrucciones, itera, descarga versiones para trabajo offline, acepta o modifica propuestas, declara integridad y finalmente sella el PF. | Recibe Paper ID y clave por canal seguro separado, verifica sello e integridad, compara el PF recibido con original y las intervenciones y consulta fichas e historial; dispone de un ZIP único. |

## 2. Ciclo del AUTOR: versiones y trabajo offline

- El AUTOR carga el manuscrito inicial una sola vez por Paper ID; el orquestador conserva original y versiones sucesivas con identificador, fecha/hora, origen y relación de precedencia. La versión de trabajo predeterminada es siempre la última; las anteriores permanecen disponibles para comparación y recuperación.
- Cada iteración con Astra parte de la última versión, salvo selección explícita de una versión anterior. «Nueva llamada al mismo módulo» reutiliza el documento ya cargado. La consola inicia Streamlit local; las llamadas se realizan desde el navegador.
- El AUTOR puede descargar la versión de trabajo, editarla offline y reimportarla con el mismo Paper ID. El sistema conserva el archivo anterior, registra la nueva versión y compara ambos DOCX para identificar cambios introducidos durante el trabajo offline como cambios HUMANOS declarados; el análisis automático de diferencias no demuestra por sí solo autoría humana.

## 3. Nivel 1: SEIS INSTRUCCIONES del AUTOR

| INSTRUCCIÓN | Alcance |
|---|---|
| Traducción | Traducción fiel entre idiomas, sin nuevos hallazgos. |
| Corrección | Lenguaje, estilo, terminología y claridad, preservando el significado. |
| Revisión bibliográfica | Evaluación, búsqueda, sugerencia y verificación de referencias; aprobación humana. |
| Datos y resultados | Interpretación de datos y resultados del manuscrito, asumidos correctos; sin bases externas ni recálculos por defecto. |
| Argumentación | Tesis, premisas, inferencias, contraargumentos y conclusiones. |
| Coherencia integral | Relación global entre objetivos, marco teórico, metodología, resultados, discusión y conclusiones. |

Cada instrucción tiene un prompt general propio y admite instrucciones particulares por llamada e iteraciones sucesivas.

### 3.1. Prompts generales de las seis instrucciones

#### Traducción

**Prompt general:**

Actúa como asistente de traducción académica. Traduce únicamente el contenido solicitado al idioma indicado, preservando sentido, estructura argumental, citas, nombres propios, referencias, datos, cifras y cautelas epistémicas. No añadas ideas, bibliografía ni resultados. Si un término admite traducciones sustantivamente distintas, señala la ambigüedad. Devuelve el texto propuesto y un registro localizable de cambios; distingue cualquier explicación de la traducción.

#### Corrección

**Prompt general:**

Revisa ortografía, gramática, puntuación, terminología, fluidez y claridad académica del texto indicado. Conserva tesis, resultados, matices, referencias y significado. No inventes hechos ni amplíes el argumento salvo solicitud expresa. Devuelve una versión corregida y diferencias localizables; señala separadamente cambios que podrían afectar el sentido para aprobación del AUTOR.

#### Revisión bibliográfica

**Prompt general:**

Examina las referencias y las citas del manuscrito. Cuando existan herramientas de consulta disponibles, contrasta DOI, autores, título, año y publicación con Crossref, OpenAlex, PubMed, Semantic Scholar o editoriales, según pertinencia. Clasifica cada referencia como verificada, parcialmente verificada, no verificada o discrepante, indicando evidencia y fuente de comprobación. Verificar la existencia de una referencia NO prueba que respalde la afirmación citada: señala cuándo se requiere lectura de contenido. Nunca inventes fuentes ni DOI. Propón correcciones o referencias adicionales solo como sugerencias sujetas a aprobación del AUTOR; si no tienes acceso a fuentes externas, decláralo.

#### Datos y resultados

**Prompt general:**

Interpreta únicamente los datos, tablas, cifras y resultados ya reportados en el manuscrito, tomando sus cálculos como supuestos correctos a efectos de la tarea. Identifica tendencias, alcance interpretativo, incertidumbres y límites argumentativos. No ejecutes análisis estadísticos nuevos, no agregues bases externas, no modifiques cifras y no atribuyas a Astra cálculos que no realizó. Señala posibles inconsistencias únicamente como advertencias no verificadas; distingue observación, inferencia y sugerencia.

#### Argumentación

**Prompt general:**

Analiza la estructura de la argumentación académica: tesis, premisas, inferencias, evidencia, objeciones, contraargumentos y conclusiones. Identifica debilidades y propone mejoras concretas con ubicación textual. Distingue entre reformulación de ideas ya presentes y propuesta conceptual potencialmente nueva, que deberá contrastarse con el manuscrito original antes de atribuirla a IA.

#### Coherencia integral

**Prompt general:**

Evalúa el manuscrito completo en términos de coherencia entre problema, objetivos, marco teórico, método, resultados, discusión, conclusiones y bibliografía. Detecta contradicciones, vacíos, desajustes y repeticiones; ofrece recomendaciones localizables y priorizadas. No inventes resultados ni cambies la tesis sin aprobación del AUTOR. Diferencia correcciones formales de cambios conceptuales y justifica cualquier aporte que parezca nuevo respecto del original.

## 4. Captura automática de iteraciones

- **Metadatos:** herramienta IA, proveedor, modelo y versión real, contexto de acceso/API y configuración efectiva.
- **Por llamada:** Paper ID, ID de iteración, fecha/hora, identificador y fecha de versión, INSTRUCCIÓN, prompt general, instrucciones específicas, contenido enviado, respuesta íntegra, cambios del AUTOR en nueva instrucción, diferencias antes/después y vínculo con iteraciones anteriores.
- **Por propuesta:** fragmento original, texto sugerido, clasificación FAIA, justificación de novedad y localización. Registrar decisiones de aceptación, modificación, rechazo o pendiente cuando existan; no atribuir decisiones al AUTOR sin su confirmación.
- La comparación de una propuesta con el original es obligatoria antes de calificarla como aporte conceptual nuevo de Astra. Registrar incertidumbre, falsos positivos posibles y la evidencia utilizada.
  
- **Identificación de cambios humanos:** Astra compara la versión anterior con la versión reimportada y describe las modificaciones, su naturaleza y su posible significado. No pretende demostrar que fueron realizadas por una persona.
- **Persistencia de aportes de IA:** Astra compara sus contribuciones anteriores con la versión reimportada y determina si cada aporte permanece literalmente, permanece conceptualmente reformulado o desapareció. Para cada conclusión proporciona evidencia textual y un nivel de incertidumbre.
  
- Los errores de API, reintentos, cambios de versión y fallos de validación también se registran para reconstruir la secuencia.

## 5. Profundidad FAIA

**¿Qué significa «profundidad FAIA»?**

Es la categoría de actividad de IA que describe la intervención efectivamente realizada, no es una escala necesariamente ordinal. Astra propone una clasificación para cada intervención; el AUTOR puede revisarla y el sistema conserva la clasificación original y su justificación. Las seis categorías provienen del vocabulario FAIA [F1–F3].

| Profundidad FAIA | Definición operativa |
|---|---|
| Refinement | Ajuste menor que preserva estructura y sentido. |
| Enhancement | Extensión o mejora de estructura/contenido. |
| Transformation | Reexpresión. |
| Analysis | Interpretación. |
| Contribution | Aporte parcial intelectual o creativo de IA. |
| Co-Creation | Producción sustantiva conjunta humano–IA. |

La IA define inicialmente qué categoría FAIA realizó y explica por qué. La categoría se determina por el contenido efectivamente generado, no automáticamente por el nombre de la INSTRUCCIÓN.

## 6. Declaración de integridad y confidencialidad del AUTOR

La declaración se presenta antes del sellado, queda fechada y vinculada al Paper ID y a la versión exacta del PF. Su aceptación debe ser expresa y registrable. El texto de referencia es:

> «Declaro, bajo mi responsabilidad, que he informado de buena fe todos los usos relevantes de herramientas de inteligencia artificial efectuados en la preparación y revisión de este manuscrito, tanto dentro como fuera del orquestador, antes y durante el proceso. Declaro haber revisado críticamente las respuestas y modificaciones incorporadas, comprobado en la medida correspondiente la exactitud de las afirmaciones, referencias y resultados, y asumir la responsabilidad íntegra por el contenido del Paper Final. Asimismo, declaro que no he incorporado, cargado ni utilizado en las solicitudes a herramientas de IA información confidencial, no pública o identificable de terceros sin contar previamente con las autorizaciones o consentimientos válidos que correspondan. Reconozco que las solicitudes efectuadas mediante la API transmiten al proveedor el contenido enviado, sujeto a sus condiciones, políticas y medidas de tratamiento de datos. Confirmo que el archivo identificado como Paper Final es la versión que remitiré al EDITOR, sin modificaciones posteriores al sellado. Fecha: [automática]. Paper ID: [automático]. Versión y huella del PF: [automáticas]. Identificación del AUTOR: [campo]. Aceptación expresa: [campo]».

El sistema debe impedir continuar sin aceptación.

## 7. Finalización del Paper Final y sellado

**Sellado de Paper Final (PF).** Hasta el cierre pueden realizarse iteraciones e importaciones offline; después del cierre no se permiten nuevas llamadas, nuevas cargas ni modificaciones del PF para ese expediente.

- Botón exclusivo «Finalizar y sellar auditoría»: comprueba secuencia, existencia de versión final, declaración y coherencia de metadatos; fija el PF exacto, congela el historial completo y calcula SHA-256 sobre bytes definidos y documentados.
- Obtiene un token RFC 3161 de una autoridad TSA independiente y verifica firma, certificado/cadena, huella y tiempo antes de anunciar éxito; ante fallo, no se declara sellado.
- El PF que se remite al EDITOR debe ser idéntico byte a byte al PF sellado; su SHA-256 debe coincidir. No se exige que el PF sea idéntico al manuscrito original ni a cada versión intermedia: eso sería incompatible con la revisión del paper.
- Una modificación posterior, incluso humana y mínima, rompe la coincidencia criptográfica. Si se requiere cambiar el texto, no se presenta como PF ya sellado: deberá iniciarse un nuevo expediente/versionado final con nueva declaración y nuevo sellado, sin sobrescribir el anterior.
- AES-256-GCM protege el expediente privado; SHA-256 permite comprobar integridad; RFC 3161 acredita existencia temporal de una huella, no integridad ética del proceso ni veracidad de la captura [T1–T2].

## 8. Entregables al AUTOR

| Entregable | Regla |
|---|---|
| `Paper_Final.docx` | Texto procesado sin marcas ni comentarios. |
| `Paper_anotado.docx` | Solo resaltado: verde para modificaciones incorporadas por IA, amarillo para incertidumbre que declara IA como novedad IA. |
| `Informe_extenso_uso_IA.docx` | Word editable con módulos, prompts, intervenciones y todas las decisiones, para adaptar al Journal. |
| ZIP de auditoría | Historial íntegro, respuestas completas, diffs, versiones, verificaciones, decisiones, metadatos y evidencias. |

El archivo `Paper_Final.docx` será el PF final limpio destinado al EDITOR.

## 9. Auditoría del EDITOR

- El EDITOR recibe Paper ID y clave por canal seguro separado; abre la interfaz estática de GitHub Pages y verifica/desencripta el expediente localmente en su navegador.
- El EDITOR carga el PF recibido y el sistema comprueba coincidencia criptográfica con la huella del PF sellado. Si no coincide, muestra error de integridad y no lo presenta como versión certificada.
- El sistema contrasta manuscrito original, iteraciones registradas, modificaciones humanas —incluidas las offline reimportadas— y PF sellado.
- En `Paper_anotado.docx` del EDITOR: verde = texto de Astra conservado literalmente; amarillo = aporte conceptual realmente nuevo de Astra conservado tras reescritura humana, con evidencia e incertidumbre; sin marca = descartado o atribución insuficiente.
- El Word editorial solo contiene resaltados; las explicaciones se muestran en fichas interactivas. Cada ficha representa una contribución; «Ver las iteraciones» despliega todas sus llamadas, prompts, respuestas y diferencias, sin omitir rechazos.
- Una sola descarga editorial: ZIP con `Paper_anotado.docx`, historial íntegro de intervenciones —incluidas las descartadas—, informe derivado de comparación, declaración de integridad del AUTOR y token(es) RFC 3161.

La comparación editorial se efectúa localmente en el navegador.

## 10. Referencias

**[F1]** Le Dévédec, S. E., Hettne, K., Gambardella, A., Schultes, E. y Posth, S. (2026). *FAIA – FAIR AI Attribution White Paper*, v0.9. Zenodo.  
https://zenodo.org/records/20083769

**[F2]** FAIA. *Vocabulary*.  
https://faia.liccium.com/technology/vocabulary

**[F3]** FAIA. *Implementation*.  
https://faia.liccium.com/technology/implementation

**[P1]** Garcia, M. B. (2026). *PETMALU-AI: A Reporting Checklist for Transparent and Accountable Generative AI-Assisted Research Writing*. Education Sciences, 16(7), 1127.  
https://doi.org/10.3390/educsci16071127

**[P2]** PETMALU-AI. *Printable Checklist*.  
https://manuelgarcia.info/petmalu-ai/downloads/PETMALU-AI_Printable_Checklist.html

**[T1]** Adams, C. et al. (2001). *Internet X.509 Public Key Infrastructure Time-Stamp Protocol*. RFC 3161.  
https://www.rfc-editor.org/rfc/rfc3161

**[T2]** Cooper, D. et al. (2008). *Internet X.509 Public Key Infrastructure Certificate and CRL Profile*. RFC 5280.  
https://www.rfc-editor.org/rfc/rfc5280

**[E1]** ICMJE (2026). *Use of AI by Authors*.  
https://icmje.org/recommendations/browse/artificial-intelligence/ai-use-by-authors.html

**[E2]** ICMJE (2026). *Use of Artificial Intelligence in Publishing*.  
https://icmje.org/recommendations/browse/artificial-intelligence/

**[E3]** Zielinski, C. et al. (2023). *Chatbots, generative AI, and scholarly manuscripts: WAME recommendations*.  
https://doi.org/10.25100/cm.v54i3.5868

**[E4]** COPE Council. *Authorship and AI tools*.  
https://doi.org/10.24318/cCVRZBms

**[E5]** Elsevier. *Generative AI policies for journals*.  
https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals

**[E6]** Nature Portfolio. *Artificial Intelligence (AI): Scientific Reports policy*.  
https://www.nature.com/srep/journal-policies/ai

**[E7]** Springer Nature. *Humanities and Social Sciences Communications editorial policies*.  
https://www.nature.com/palcomms/journal-policies/editorial-and-publishing-policies

## Anexo 1 · Fraude residual y límites

| Riesgo u omisión | Control paliativo |
|---|---|
| IA previa al registro | Declaración. |
| IA externa paralela | Declaración. |
| Software manipulado (sello no prueba captura veraz) | Versionado y auditoría de código. |
| Atribución intelectual engañosa (incertidumbre) | Declaración. |
| Declaración falsa | Responsabilidad AUTOR. |
| Resultados inventados por IA | Responsabilidad AUTOR. |

**Fórmula pública de alcance:**

> «El software proporciona un registro verificable y resistente a alteraciones de las intervenciones de IA capturadas dentro de su entorno auditado; no garantiza que se hayan declarado todos los usos de IA realizados fuera de él».

## Anexo 2 · Arquitectura mínima de /publicaciones/IA/

GitHub Pages publica únicamente interfaz y metadatos no sensibles, `auditoria.enc` y `auditoria.tsr`. No publica API keys, claves de descifrado, manuscritos ni prompts en claro. La interfaz de AUTOR es Streamlit local; las llamadas a Astra transmiten contenido a la API.

| Ubicación | Función |
|---|---|
| `bio/publicaciones/IA/index.html`; `auditor.js`; `estilos.css` | Interfaz editorial estática en GitHub Pages. |
| `bio/publicaciones/IA/orquestador/app.py` | Streamlit local del autor. |
| `orquestador/config.py`; `requirements.txt` | Modelo, API y dependencias. |
| `orquestador/modulos/` | `traduccion.py`, `correccion.py`, `bibliografia.py`, `datos_resultados.py`, `argumentacion.py`, `coherencia_integral.py`. |
| `orquestador/auditoria/` | `registro.py`, `diferencias.py`, `cifrado.py`, `sellado_rfc3161.py`. |
| `registros/PUB-AAAA-NNNN/` | `metadata.json`, `auditoria.enc`, `auditoria.tsr`; etapas adicionales vinculadas. |

«Astra High» es denominación funcional. El identificador y parámetros reales del modelo deberán confirmarse en la API durante la implementación. Las rutas son la estructura técnica prevista y no acreditan que los archivos ya existan.

### Pendientes de pruebas

- Definir TSA, política de certificados, verificación RFC 3161 y preservación temporal a largo plazo.
- Fijar canonización, orden de eventos, bytes de SHA-256, manifiesto y vínculo entre PF, historial, cifrado y sello.
- Probar AES-GCM, gestión de claves, dependencias web, ausencia de telemetría y privacidad del PF.
- Verificar conservación fiel de tablas, notas, referencias y resaltados en DOCX.
- Probar captura de errores/reintentos, importación offline, control de versiones, fallo de sellado, rechazo de cambios posteriores y coincidencia del PF recibido por el EDITOR.
- No afirmar que el software está implementado, certificado o validado hasta completar pruebas en bio/test-IA.
