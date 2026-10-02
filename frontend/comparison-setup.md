# Comparativa del último entrenamiento

Actualiza la integración, incluido el nuevo `api/comparison.py`, y reinicia Home
Assistant. Añade este recurso de tipo **Módulo JavaScript**:

`/wger/frontend/wger-comparison-card.js?v=26.10.1`

Añade una tarjeta manual:

```yaml
type: custom:wger-comparison-card
entity: sensor.workout_comparison
title: Tu última sesión, en contexto
```

Comprueba el identificador real del sensor si Home Assistant le añade un sufijo.

## Selección y métricas

Se toma la sesión finalizada con el inicio más reciente. Se busca la sesión
finalizada anterior cuyo `routine` y `day` coincidan. Una sesión aún abierta no
sustituye a la última finalizada. Si falta la asociación con el día de rutina, no
se intenta adivinar una equivalencia por nombre o ejercicios.

La tarjeta muestra el nombre del día de rutina de ambas sesiones, además de
valores actuales, anteriores, diferencias absolutas y porcentuales de series,
repeticiones, volumen y duración. Las fechas se presentan
en la zona horaria de Home Assistant. Cada registro de ejercicio cuenta como una
serie; la duración procede del inicio y fin de la sesión. Si cambian los ejercicios
registrados, se indica en la tarjeta.

- Las cargas en lb se convierten a kg con el factor 0.45359237.
- Volumen significa carga en kg multiplicada por repeticiones.
- No se calcula el volumen completo si algún registro carece de carga o usa
  peso corporal, placas, velocidad u otra unidad no convertible.
- Tiempo y distancia no se suman como repeticiones. Si aparecen en alguna sesión,
  la comparación total de repeticiones y volumen queda sin valor, con explicación.
- Los valores ausentes no se convierten en cero. Si el valor anterior es cero,
  se muestra la diferencia absoluta sin inventar un porcentaje.
- Las variaciones son neutrales: más volumen o menos duración no se presentan
  automáticamente como una mejora.

No hay paginación. Cada consulta de registros se filtra por la sesión exacta y
solicita hasta 999 resultados. Si faltan resultados, no se muestran totales
parciales. Las consultas se repiten en el intervalo existente de 30 minutos.
La comparación requiere hasta siete peticiones adicionales por actualización,
incluida la consulta del nombre del día de rutina.
No modifica datos en wger.

## Comprobación manual

1. Comprueba las fechas de las dos sesiones en wger: deben corresponder al mismo
   día de la misma rutina.
2. Contrasta series y duración con los registros originales.
3. Si ves «No comparable», revisa las unidades y los valores ausentes indicados.
4. Si solo has realizado ese día una vez, la tarjeta mostrará que falta una sesión
   anterior. Aparecerá la comparación al registrar y finalizar la siguiente.
