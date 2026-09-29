# Historial visual de entrenamientos

Actualiza la integración y reinicia Home Assistant. Añade este recurso de tipo
**Módulo JavaScript** en Ajustes → Paneles de control → Recursos:

`/wger/frontend/wger-workout-history-card.js?v=3`

Después añade una tarjeta manual:

```yaml
type: custom:wger-workout-history-card
title: Explorar entrenamientos
```

La tarjeta ajusta su altura al contenido. Si ya la tenías añadida, cambia el
recurso a `?v=3` y recarga el panel. En una vista de Secciones,
elimina cualquier `grid_options.rows` fijo que hayas añadido a esta tarjeta.

Si tienes varias cuentas de Wger configuradas, indica el ID de la entrada que
quieres consultar:

```yaml
type: custom:wger-workout-history-card
entry_id: TU_ID_DE_ENTRADA
```

El selector carga los 20 entrenamientos finalizados más recientes. Al elegir
uno, la tarjeta consulta sus registros completos y muestra fechas, duración,
totales, gráficas, ejercicios y cada serie con sus objetivos registrados. El
detalle se pide solo para la sesión elegida. La gráfica muscular es una
estimación calculada a partir del volumen y los músculos asociados al ejercicio.
El volumen se muestra en kg × repeticiones; las cargas en lb se convierten a kg.
Si algún registro usa una unidad no convertible, el volumen aparece sin valor.
Si Wger indica que faltan registros en la respuesta, la tarjeta muestra un error
en vez de presentar un detalle parcial.
