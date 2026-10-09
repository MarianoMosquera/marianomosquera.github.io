# Orquestador de diversidad semántica mediante embeddings

**Proyecto:** Deliberación multiagente — caso Tambogrande (Perú)  
**Objeto:** Evaluación exploratoria de diversidad semántica entre posiciones argumentativas antes y después de una intervención semántica basada en SKOS.

## Arquitectura y procedencia

Este módulo funciona **independientemente de MALLM** y no modifica su código ni sus checkpoints. `extractor.py` lee `../mallm/experiments/tambogrande/checkpoints/round2.json` y extrae, para los ocho agentes, los campos `additional_args.skos.first_draft_message` y `additional_args.skos.second_draft_message` de los registros de `globalMemory` correspondientes a `turn == 1`. **First Draft y Second Draft son dos versiones dentro de la primera ronda; no representan las rondas 1 y 2 de MALLM.** Los textos se guardan localmente en `resultados/drafts_extraidos.json` (excluido de Git; los originales permanecen en el checkpoint).

- `extractor.py`: extrae las 16 posiciones argumentativas completas (`message`, no `solution`).
- `comparar.py`: obtiene 16 embeddings con `text-embedding-3-large`, calcula distancias coseno para los 28 pares no ordenados de agentes en cada etapa y exporta `resumen.json` y `comparaciones.csv`.
- `robustez.py`: conserva los First Drafts y trunca cada Second Draft al número de tokens de su First Draft; repite el cálculo y exporta `robustez_longitud.json` y `robustez_pares.csv`.

## Indicador y fundamento metodológico

Para cada etapa \(t\), con \(n=8\) agentes y vector \(v_{i,t}\) del mensaje completo del agente \(i\), se define:

\[
D_t=\frac{2}{n(n-1)}\sum_{i<j}\left(1-\frac{v_{i,t}\cdot v_{j,t}}{\lVert v_{i,t}\rVert\lVert v_{j,t}\rVert}\right).
\]

La **distancia coseno media entre pares** resume la dispersión semántica del conjunto; se calculan \(\binom{8}{2}=28\) distancias por etapa. La variación porcentual es \(100(D_{second}-D_{first})/D_{first}\). Valores mayores indican mayor dispersión en el espacio vectorial del modelo.

Reimers y Gurevych (2019) fundamentan la comparación de representaciones semánticas mediante similitud coseno, **aunque su trabajo utiliza SBERT, no el modelo de OpenAI empleado aquí**. Tevet y Berant (2021) justifican evaluar críticamente las métricas automáticas de diversidad. Stasaski y Hearst (2022) muestran una alternativa basada en inferencia del lenguaje natural (NLI), útil para diferenciar distancia semántica de contradicción argumentativa. **Ninguno de estos trabajos valida directamente este índice para ocho agentes ni el efecto de SKOS**: la fórmula agregada es una operacionalización definida para este experimento.

## Resultados del caso Tambogrande

| Medición | First Draft | Second Draft | Diferencia absoluta | Variación |
|---|---:|---:|---:|---:|
| Textos completos | 0,134435 | 0,127624 | −0,006811 | **−5,07 %** |
| Sensibilidad: Second Draft truncado por agente | 0,134435 | 0,138518 | +0,004083 | **+3,04 %** |

En los textos completos se observa menor dispersión semántica después de SKOS. Sin embargo, al igualar la longitud mediante truncamiento inicial, la dirección se invierte. **Por tanto, estos resultados no aportan evidencia robusta de homogeneización semántica asociada con SKOS.** Esto **no demuestra ausencia de homogeneización** ni permite identificar un efecto causal de SKOS.

## Limitaciones e interpretación

- Los Second Drafts completos son más extensos que los First Drafts; la longitud y el contenido adicional pueden afectar las representaciones.
- La prueba de robustez **no aísla únicamente el efecto de longitud**: al truncar desde el final también se omiten argumentos y se privilegia el comienzo de los documentos. Es un análisis de sensibilidad al procedimiento de recorte, no un control definitivo.
- La distancia coseno de embeddings no equivale directamente a pluralismo de valores, desacuerdo político, contradicción o calidad deliberativa.
- Se trata de un único caso con ocho agentes y sin replicaciones ni grupo de control; no se realiza inferencia causal ni prueba de significación estadística.
- Los resultados dependen del modelo `text-embedding-3-large`, de los textos concretos y de las decisiones de procesamiento.

## Reproducción

Desde la raíz `deliberacion/`, con un entorno Python que disponga de `openai` y `tiktoken` y una variable de entorno `OPENAI_API_KEY` configurada:

```bash
python embeddings/extractor.py
python embeddings/comparar.py
python embeddings/robustez.py
```

La extracción no consume API; las dos mediciones posteriores sí generan solicitudes de embeddings. No almacenar claves en el repositorio. El archivo `drafts_extraidos.json` se genera localmente y está excluido por `.gitignore`.

## Referencias académicas

1. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP-IJCNLP, 3982–3992. https://doi.org/10.18653/v1/D19-1410
2. Tevet, G., & Berant, J. (2021). *Evaluating the Evaluation of Diversity in Natural Language Generation*. EACL, 326–346. https://doi.org/10.18653/v1/2021.eacl-main.25
3. Stasaski, K., & Hearst, M. (2022). *Semantic Diversity in Dialogue with Natural Language Inference*. NAACL-HLT, 85–98. https://doi.org/10.18653/v1/2022.naacl-main.6
