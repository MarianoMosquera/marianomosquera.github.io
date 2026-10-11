"""Resumen descriptivo de estimaciones explícitas de Astra, sin inferir valores."""
from math import isfinite

RANGOS = ((0, 25), (25, 50), (50, 75), (75, 100))


def resumir_atribuciones(evaluacion):
    """Cuatro intervalos disjuntos: [0,25], (25,50], (50,75], (75,100]."""
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
        p = contribucion.get('porcentaje_estimado')
        if color == 'verde':
            continue  # La atribución total no participa de los cuartiles.
        if p is None:
            resumen['sin_porcentaje'] += 1
            continue
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not isfinite(p) or not 0 <= p <= 100:
            raise ValueError('Porcentaje de atribución inválido')
        indice = 0 if p <= 25 else 1 if p <= 50 else 2 if p <= 75 else 3
        resumen['cuartiles'][indice] += 1
        resumen['porcentajes'].append(p)
    return resumen
