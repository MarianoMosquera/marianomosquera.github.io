# Deliberación multiagente con MALLM y ontología SKOS

## Descripción

Este directorio documenta una extensión experimental de **MALLM
(Multi-Agent Large Language Models)** orientada al estudio de
deliberación multiagente asistida por una ontología externa SKOS. La
implementación conserva la arquitectura deliberativa general de MALLM,
pero incorpora modificaciones para: usar perfiles predefinidos; producir
y preservar posiciones iniciales independientes; reinterpretarlas
mediante SKOS antes de la deliberación; garantizar simetría
informacional; separar posiciones deliberativas de alternativas de
decisión; realizar *Approval Voting* anónimo; y mantener checkpoints
auditables y reanudables.

La primera aplicación se realizó sobre **Tambogrande (Perú)** con ocho
agentes y corte temporal en enero de 2002. La ejecución utilizó **GPT-6
Astra** con `reasoning_effort="xhigh"`.

## 1. Modificaciones a MALLM

### Perfiles predefinidos

Se incorporó un generador `predefined`. Los ocho agentes representan a:
Manhattan Minerals; Centromin Perú; Ministerio de Energía y Minas;
Municipalidad; Frente de Defensa del Valle de San Lorenzo y Tambogrande;
Productores agrícolas y Junta de Regantes del Valle de San Lorenzo; Mesa
Técnica; y Sociedad Nacional de Minería, Petróleo y Energía.

El perfil es estable, pero la posición concreta ante el caso no está
predeterminada: emerge de la interacción entre perfil, contexto y LLM.

### First Draft independiente

La primera ronda fue modificada para que **todos los agentes produzcan
una posición inicial propia antes de cualquier deliberación
interagente** (`all_agents_generate_first_draft=True`). Así, ningún
First Draft depende de una respuesta previa de otro agente.

### Intervención semántica SKOS

Después de cada First Draft se incorporó una etapa de procesamiento
mediante una ontología externa **SKOS/RDF (TTL)**, distribuida en once
archivos TTL y organizada en cuatro dimensiones: **Gobernanza, Valores,
Agenda y Racionalidad**.

SKOS no prescribe la posición del agente. Opera después de la respuesta
inicial como estructura semántica para reinterpretar y profundizarla. El
resultado se conserva como **Second Draft**:

`Perfil + contexto → First Draft → SKOS → Second Draft`

En Tambogrande se observó un **cambio sustantivo** entre ambos estados.
Los Second Drafts conservaron la perspectiva diferenciada de cada actor,
pero desarrollaron con mayor profundidad dimensiones normativas,
institucionales, argumentativas y de gobernanza que aparecían de forma
más limitada o implícita en los First Drafts. "Cambio sustantivo"
describe aquí una observación cualitativa; no implica significación
estadística.

El Second Draft sustituye al First Draft como estado activo para la
deliberación posterior, aunque ambos quedan preservados para
trazabilidad y comparación.

## 2. Deliberación simétrica

R2 fue modificada para garantizar **simetría informacional**. Al
iniciarse la ronda, cada uno de los ocho agentes recibe los mismos ocho
Second Drafts.

La implementación elimina dos posibles asimetrías: ningún agente dispone
de un `current_draft` privilegiado y ninguno observa las respuestas R2
que los demás están generando durante esa misma ronda. Por ello, cada
respuesta R2 se genera a partir del mismo estado informacional previo:

`8 Second Drafts → contexto común → 8 posiciones deliberativas R2`

Esto evita que el orden de ejecución otorgue a los agentes posteriores
información deliberativa adicional.

## 3. Separación entre deliberación y decisión

Al terminar la ronda se extrae de cada posición deliberativa una **Final
Answer** que funciona exclusivamente como alternativa candidata para la
decisión.

Se modificó MALLM para impedir que `generate_final_answers()`
sobrescriba la posición deliberativa almacenada en `Agreement.solution`.
La distinción es esencial:

-   **posición deliberativa R2**: estado argumentativo que alimentaría
    una ronda posterior;
-   **Final Answer R2**: alternativa derivada de ese estado para la
    votación.

Por tanto, si hubiera R3, esta continuaría desde las ocho posiciones
deliberativas R2 y no desde las Final Answers. La generación de
alternativas de decisión no altera la memoria deliberativa.

## 4. Approval Voting anónimo

La decisión comienza al finalizar R2 mediante **Approval Voting**. Las
ocho Final Answers se presentan anónimamente: el votante evalúa su
contenido sin conocer qué agente produjo cada alternativa. Cada agente
puede aprobar una o varias opciones.

Un máximo único de aprobaciones determina el ganador; no se exige
mayoría absoluta. Si existe empate en el máximo, continúa la
deliberación. Se estableció un máximo de cuatro rondas:

`R1 → SKOS → R2 → voto → [R3 → voto] → [R4 → voto]`

Un empate después de R4 finaliza como **sin acuerdo**, sin R5. El
anonimato se aplica a las alternativas sometidas a votación; durante la
deliberación los agentes conservan sus roles.

## 5. Checkpoints y reanudación

Se incorporaron checkpoints explícitos para R1 y R2. Estos preservan
turno, identificadores, orden de agentes, memoria global,
acuerdos/posiciones, drafts pertinentes y resultados del proceso de
votación.

El checkpoint R2 se escribe de forma atómica y su carga valida tipo de
checkpoint, turno, orden de personas y presencia de las ocho memorias y
acuerdos. Cuando corresponde, los identificadores almacenados se
remapean a los de la nueva ejecución.

El objetivo es que **detener el experimento después de R2 y reanudarlo
sea lógicamente equivalente a una ejecución continua**: no se repiten
llamadas ya completadas y una eventual R3 recibe el mismo estado
deliberativo previo.

## 6. Configuración de Tambogrande

El caso se configuró con ocho agentes y **corte temporal en enero de
2002**, evitando presuponer el desenlace histórico posterior. La
instrucción principal fue:

> Analiza el contexto planteado y formula una posición desde el rol
> asignado.

Configuración central:

-   modelo: `gpt-6-astra`;
-   razonamiento: `xhigh`;
-   agentes: 8;
-   `agent_generator`: `predefined`;
-   `discussion_paradigm`: `memory`;
-   `response_generator`: `critical`;
-   `decision_protocol`: `approval_voting`;
-   máximo de rondas: 4;
-   SKOS habilitado;
-   First Draft independiente para todos los agentes;
-   `max_tokens`: 24.000.

## 7. Resultados

R1 produjo correctamente **ocho First Drafts y ocho Second Drafts**. La
intervención SKOS generó el cambio cualitativo señalado: mayor
profundidad y explicitación de dimensiones normativas, institucionales,
justificativas y de gobernanza, sin eliminar la diferenciación entre
actores. Los ocho Second Drafts ---no los First Drafts--- constituyeron
el estado común de entrada a la deliberación simétrica.

R2 produjo ocho posiciones deliberativas y, a partir de ellas, ocho
Final Answers. El *Approval Voting* anónimo arrojó:

  Alternativa originada en                             Aprobaciones
  -------------------------------------------------- --------------
  Mesa Técnica                                              **8/8**
  Manhattan Minerals                                            7/8
  Centromin Perú                                                7/8
  Ministerio de Energía y Minas                                 7/8
  Municipalidad                                                 7/8
  Productores agrícolas / Junta de Regantes                     7/8
  Sociedad Nacional de Minería, Petróleo y Energía              7/8
  Frente de Defensa                                             6/8

La alternativa de la **Mesa Técnica fue el único máximo, con 8/8
aprobaciones**. El sistema declaró acuerdo al finalizar R2 y no ejecutó
R3. Esto no significa que los ocho agentes produjeran posiciones
idénticas: la convergencia fue sobre la aceptabilidad de una
alternativa. De hecho, la Mesa Técnica fue el votante más restrictivo y
aprobó únicamente su propia opción.

## 8. Alternativa ganadora

La Final Answer originada en la Mesa Técnica fue el **"Protocolo de
Descarte Temprano y Verificación Pública"**. Es una de las ocho
alternativas "síntesis" derivadas de R2 y resultó ganadora por aprobación unánime.

Su aporte central consiste en desplazar el objeto del acuerdo. En lugar
de exigir una decisión inmediata a favor o en contra de la explotación,
propone acordar **las condiciones bajo las cuales el proyecto puede
continuar, debe reformularse o debe descartarse**.

El protocolo articula siete componentes:

1.  reconocer desacuerdos que los estudios técnicos no pueden resolver
    por sí solos;
2.  acordar pruebas y criterios antes de conocer sus resultados;
3.  distinguir incertidumbre investigable de incertidumbre incompatible
    con avanzar;
4.  separar asesoramiento a la población y revisión técnica
    independiente;
5.  comparar alternativas sin fabricar un ganador económico;
6.  distinguir habilitación jurídica y condiciones de aceptación;
7.  convertir acuerdos en obligaciones y decisiones verificables.

Admite diferentes desenlaces: completar evidencia, reformular y
reevaluar, recomendar la no autorización ante deficiencias sustantivas o
reconocer la persistencia del desacuerdo territorial. El avance queda
condicionado a evidencia suficiente, habilitación legal, aceptación
conforme al procedimiento acordado y capacidad efectiva de cumplimiento.

El resultado puede interpretarse como un **metaacuerdo procedimental**:
la convergencia no exige que los agentes abandonen sus intereses o
adopten una valoración sustantiva única del proyecto, sino que acepten
reglas comunes para establecer cuándo una decisión puede considerarse
suficientemente fundada y legítima.

## 9. Alcance y límites

El experimento separa analíticamente tres mecanismos:

1.  generación autónoma de posiciones iniciales;
2.  intervención semántica mediante SKOS;
3.  deliberación interagente y decisión anónima.

Se trata de una simulación basada en LLM y no de una reconstrucción de
las preferencias reales de los actores históricos. La mayor profundidad
observada entre First Draft y Second Draft es por ahora un resultado
cualitativo. El análisis cuantitativo de diversidad semántica,
convergencia u homogeneización debe realizarse separadamente y controlar
factores como la diferencia de longitud entre textos.

## 10. Reproducibilidad

Los registros del experimento se conservan en
`experiments/tambogrande/`, incluyendo configuración, ejecuciones por
agente, checkpoints de R1 y R2 y output consolidado. Existe además una
copia de respaldo versionada.

El estado del código y de los resultados hasta R2 quedó respaldado en
Git en:

`1dc89a4 — Backup complete Tambogrande experiment through Round 2`

Este README describe la **versión modificada de MALLM utilizada en este
experimento** y no la distribución original del framework.
