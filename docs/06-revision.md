# Revisión y estado del proyecto

[← Desarrollo y API](05-desarrollo.md) · [Inicio](../README.md)

Revisión realizada el 7 de septiembre de 2026. Esta página registra el alcance
y los resultados de esta revisión; no sustituye un historial completo de cambios.

## Correcciones y limpieza

| Problema observado | Cambio |
| --- | --- |
| Una pareja «No paralelas» impedía también impartir la misma asignatura a la vez en aulas distintas. | Se excluye la presencia simultánea de las dos asignaturas de la pareja, conservando la simultaneidad de una sola. |
| Dobles turnos dependían del orden físico de las franjas. | Se ordenan por día/turno y se relacionan parejas por ambos extremos. |
| Había variables y una maximización redundantes para los dobles. | Se conserva la formulación obligatoria y se elimina el objetivo que no cambiaba el número de parejas. |
| El tiempo agotado se presentaba como imposibilidad demostrada. | El mensaje distingue la búsqueda inconclusa. |
| Renombrar o borrar recursos dejaba restricciones con referencias antiguas. | Se mantienen los vínculos al renombrar y se retiran reglas huérfanas al eliminar. |
| Renombrar a un nombre existente podía combinar recursos. | Se rechazan nombres duplicados antes de modificar el estado. |
| Una frecuencia inválida podía producir un error de Tk sin tratar. | Se valida la entrada y se mantiene el editor abierto. |
| Editar una asociación de aulas no verificaba aulas desconocidas igual que añadirla. | Ambas acciones comparten lectura y validación. |
| Los profesores sin límites de aula podían quedar limitados a las aulas existentes al guardar. | Se conserva la ausencia de restricción. |
| La sincronización separaba nombres de aula por comas. | El modelo toma los nombres directamente de la lista de aulas. El formulario de asociaciones sigue usando comas como separador. |
| La configuración editable podía reconstruir y perder las franjas de un ciclo irregular al guardar. | Se conservan las franjas mientras no cambien el reloj o las dimensiones del ciclo; se serializan explícitamente. |
| Los documentos malformados podían fallar después de empezar a cargar controles. | Se centralizan comprobaciones estructurales antes de mostrar la configuración. |
| El guardado de configuración independiente no era atómico. | Los formatos comparten `storage.write_json()`. |
| Mensajes todavía mencionaban botones retirados. | Se referencia el menú Archivo actual. |
| Los valores de un centro vacío estaban dentro de Tkinter. | Se extraen a `defaults.default_planning()` para reutilizarlos sin ventana. |
| Se creaban variables Tk temporales innecesarias al refrescar sábados. | Se reutilizan las variables existentes. |

La revisión mantiene el diseño visual y las funcionalidades anteriores. No añade
un sistema de persistencia externo ni una nueva dependencia de ejecución.

## Comprobaciones realizadas

- Suite completa con sesión de escritorio: **75 pruebas superadas**.
- Ruff: análisis estático y formato de `src` y `tests`.
- Nuevos casos de regresión para incompatibilidades, dobles con franjas
  desordenadas, tiempo agotado, archivos inválidos, guardado de franjas exactas,
  renombrado y eliminación de recursos.
- Exportación de una jornada larga para comprobar una página por día.
- Ejemplos de la documentación y enlaces internos comprobados durante la revisión.

## Límites que siguen vigentes

El programa no tiene guardado automático, aviso de cambios pendientes,
histórico, base de datos, calendario con fechas ni edición manual de celdas del
horario. El solver trabaja en el hilo de la interfaz y no se puede cancelar desde
la ventana. No hay un criterio de optimización pedagógica ni garantía de solución
idéntica entre ejecuciones.

Los nombres siguen siendo los identificadores de recursos. El modelo y el JSON
admiten nombres de aula con comas, pero el campo de asociaciones utiliza comas
como separador. La vista previa del reloj es una jornada de referencia; no se
pueden editar por separado las horas de cada semana desde los formularios.

Los horarios importados se comprueban estructuralmente y por ocupación, sin
volver a demostrar todas las restricciones del solver. Los documentos de
configuración incompletos se pueden guardar; su viabilidad se decide al generar.

La versión declarada es `0.1.0`. Las dependencias tienen versiones mínimas, no un
bloqueo completo de versiones. Las comprobaciones gráficas se han hecho en macOS;
no constituyen una certificación de portabilidad a todos los escritorios.
