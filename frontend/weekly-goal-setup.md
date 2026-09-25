# Objetivo semanal

1. Reinicia Home Assistant después de actualizar los archivos de la integración.
2. En Ajustes → Dispositivos y servicios → Wger → Configurar, elige el objetivo
   semanal (1–21 sesiones, 3 por defecto). Guardar recarga la integración.
3. Añade un recurso de panel de tipo **Módulo JavaScript**:
   `/wger/frontend/wger-weekly-goal-card.js?v=1`.
4. Añade una tarjeta manual:

```yaml
type: custom:wger-weekly-goal-card
entity: sensor.weekly_goal_progress
title: Objetivo semanal
```

Comprueba el identificador real en Herramientas para desarrolladores → Estados:
Home Assistant puede añadir un sufijo si el nombre ya existe.

Entidades nuevas:

- `sensor.weekly_goal_target`: objetivo configurado.
- `sensor.weekly_goal_progress`: porcentaje, limitado al 100 %.
- `sensor.weekly_goal_remaining`: sesiones pendientes, nunca negativo.
- `binary_sensor.weekly_goal_achieved`: activado al alcanzar o superar el objetivo.

Todas incluyen los atributos `completed`, `target`, `remaining`, `progress`,
`achieved`, `week_start` y `week_end`. La tarjeta necesita solo el sensor de progreso.
El sensor existente `sensor.trainings_this_week` pasa a contar sesiones finalizadas.

Se cuentan sesiones con inicio en la semana local de lunes a domingo y fecha de
fin válida no futura, usando la zona horaria de Home Assistant. Una sesión abierta
no cuenta; una sesión que cruza medianoche se asigna al día de inicio. El objetivo
incluye todas las rutinas. No se escribe ningún dato en wger.

Se mantiene el intervalo actual de actualización de 30 minutos. Tanto una nueva
sesión como el cambio de semana se reflejan en la siguiente actualización. Para
probar inmediatamente, recarga la integración.

Prueba con un objetivo superior, igual e inferior al número de sesiones finalizadas:
la tarjeta debe mostrar progreso parcial o cumplimiento y conservar el número real
cuando se supera el objetivo. Las rachas y las notificaciones quedan para siguientes
entregas.
