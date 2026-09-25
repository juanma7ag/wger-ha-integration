# Tarjeta de constancia semanal

Actualiza los archivos de la integración, incluido el nuevo `api/consistency.py`,
y reinicia Home Assistant. Añade el recurso de tipo **Módulo JavaScript**:

`/wger/frontend/wger-consistency-card.js?v=1`

Añade una tarjeta manual:

```yaml
type: custom:wger-consistency-card
entity: sensor.weekly_streak
title: Tu constancia
```

Comprueba el identificador real de las entidades si Home Assistant les añade un sufijo.

- `sensor.weekly_streak`: semanas consecutivas cumpliendo el objetivo.
- `sensor.weekly_best_streak`: mejor racha observada en las últimas 52 semanas,
  incluida la semana actual. No es una marca de todo el historial.

La tarjeta muestra la racha actual, la mejor del período y las 12 semanas más
recientes en orden cronológico. Cada casilla indica la fecha del lunes y las
sesiones completadas frente al objetivo. La semana actual aparece resaltada.

## Cómo se calcula

Se utiliza el mismo objetivo de las opciones de Wger y la zona horaria de Home
Assistant. Solo cuentan sesiones finalizadas, según su fecha de inicio local,
de todas las rutinas. Las sesiones abiertas y las fechas de fin futuras no cuentan.

Una semana cerrada que no alcanza el objetivo rompe la racha. La semana actual
incompleta no rompe la racha previa mientras siga en curso; al alcanzar el objetivo,
suma una semana. Por ejemplo, dos semanas cumplidas y la actual aún pendiente
muestran 2; al completar la actual muestran 3.

Cambiar el objetivo recalcula todo el período con el nuevo valor: no se guardan
objetivos históricos. Si la racha alcanza el principio de la ventana consultada,
la tarjeta añade `+` porque podría ser más larga.

Se realiza una petición adicional por actualización, filtrada a 52 semanas y
limitada a 999 sesiones. No se implementa paginación. Si la API indica que faltan
resultados, los sensores quedan sin valor y la tarjeta informa de historial
incompleto, en lugar de mostrar una racha incorrecta.

Se mantiene la actualización de 30 minutos. El cambio de semana se refleja en
la siguiente actualización; puedes recargar la integración para actualizar antes.

## Prueba manual

- Comprueba las sesiones de cada semana contra wger.
- Cambia el objetivo entre 1, 2 y 3 y comprueba que se recalcula el historial.
- Verifica que una semana actual pendiente mantiene la racha de la semana anterior.
- Verifica la tarjeta en escritorio y móvil.
