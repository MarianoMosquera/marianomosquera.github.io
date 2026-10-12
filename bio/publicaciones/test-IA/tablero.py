"""Tablero de atribución: únicamente cuartiles explícitos para incertidumbre."""

CUARTILES = ('Q1', 'Q2', 'Q3', 'Q4')


def resumir_atribuciones(evaluacion):
    """Cuenta contribuciones por color y cuartil; no calcula porcentajes."""
    resumen = {'verde': 0, 'amarillo': 0, 'cuartiles': [0, 0, 0, 0],
               'sin_porcentaje': 0, 'total': 0, 'porcentajes': []}
    if evaluacion is None:
        return resumen
    for contribucion in evaluacion.get('contribuciones', []):
        color = contribucion.get('color')
        if color not in ('verde', 'amarillo'):
            raise ValueError('Color de contribución inválido')
        resumen[color] += 1
        resumen['total'] += 1
        if color == 'verde':
            continue
        cuartil = contribucion.get('cuartil')
        if cuartil not in CUARTILES:
            raise ValueError('La atribución amarilla requiere Q1, Q2, Q3 o Q4')
        resumen['cuartiles'][CUARTILES.index(cuartil)] += 1
    return resumen
