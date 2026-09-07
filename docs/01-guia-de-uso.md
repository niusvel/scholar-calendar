# Guía de uso

[Inicio](../README.md) · [Arquitectura →](02-arquitectura.md)

## Qué organiza la aplicación

Scholar Calendar distribuye sesiones de asignaturas en aulas o grupos, asignando
un profesor a cada clase. El ciclo se expresa en semanas numeradas: no utiliza
fechas del calendario, festivos ni trimestres. «Aula» puede representar el grupo
que debe recibir las clases; cada asignatura configurada se imparte en **todas**
las aulas con la misma frecuencia semanal.

Una configuración puede guardarse aunque todavía no tenga profesores o clases.
Para generar desde la interfaz necesitas al menos un aula, una asignatura y un
profesor, además de asociaciones que permitan cubrir las sesiones.

## Instalación y apertura

Ejecuta `./run_app.sh` desde el proyecto. Se puede ejecutar desde otra carpeta
usando la ruta al script: este localiza el proyecto antes de abrir la aplicación.
Reutiliza su entorno virtual en los siguientes inicios.

Para comprobar que el Python elegido dispone de Tkinter:

```sh
python3 -m tkinter
```

Debe abrir una ventana de demostración. Si falta `_tkinter`, necesitas una
instalación de Python con soporte Tcl/Tk; instalar las dependencias de este
proyecto con pip no añade ese soporte al intérprete.

La ventana principal y los diálogos de edición se colocan centrados según las
dimensiones de pantalla que proporciona Tk. No existe un selector de monitor.
Los diálogos pueden desplazarse verticalmente cuando el contenido no cabe.

## Configurar el centro

La pestaña **Configuración del centro** reúne toda la información y se desplaza
verticalmente. Los botones abren editores específicos:

| Apartado o botón | Qué modifica |
| --- | --- |
| Jornada escolar → Editar | Nombre del curso, semanas, reloj, turnos diarios y sábados. |
| Días lectivos → Editar | El mismo editor de jornada. |
| Asignaturas → Editar | Nombres, sesiones semanales por aula y turnos dobles. |
| Profesores → Editar | Altas, cambios de nombre y bajas de profesores. |
| Aulas / grupos → Editar | Altas, cambios de nombre y bajas de aulas. |
| Asociaciones | Profesores habilitados por asignatura y limitaciones de aulas. |
| Días bloqueados / Restricciones | Días no disponibles y parejas de asignaturas incompatibles. |

Los botones repetidos de **Asociaciones** comparten su diálogo. Los de **Días
bloqueados** abren el de restricciones, que es distinto al de asociaciones.

En cualquier diálogo, **Guardar cambios** aplica la edición a la configuración
en memoria. **Cancelar**, Escape o cerrar ese diálogo descarta todos los cambios
de esa edición, incluso altas y bajas. Para conservarlos en disco utiliza después
**Archivo → Guardar**. Los errores de validación mantienen abierto el editor.
Las operaciones del menú Archivo se desactivan mientras se edita.

## Jornada y reloj

| Valor inicial | Configuración |
| --- | --- |
| Ciclo | 1 semana |
| Lunes a viernes | 6 turnos por día |
| Sábado | 0 turnos, sin semanas activadas |
| Inicio | 08:30 |
| Clase | 45 minutos |
| Cambio | 5 minutos |
| Merienda | 10:05–10:25 |
| Comida | 13:40–15:00, después del turno 6 |

Introduce horas en formato `HH:MM`. Para quitar una pausa, vacía tanto su inicio
como su final. Para habilitar un sábado, indica sus turnos y marca las semanas en
las que se utiliza. Un domingo nunca se incluye.

La tabla de franjas muestra actividades, horas y duración. Los dos primeros
turnos iniciales son 08:30–09:15 y 09:20–10:05; tras la merienda, el tercero empieza
a las 10:25. No se recortan clases para hacerlas caber antes de una pausa.

La comida no añade turnos: con seis turnos la jornada termina a las 13:40. Si
habilitas un séptimo, comienza como mínimo a las 15:00. La vista del horario
muestra pausas entre clases; no añade una fila de comida después de la última
clase. Consulta [el cálculo del reloj](03-planificacion.md#el-reloj-escolar) para
entender los huecos y las pausas.

## Recursos y asociaciones

Añade asignaturas con una frecuencia entera positiva. Por ejemplo, «Matemáticas,
3 sesiones» significa tres sesiones por semana en **cada aula**, no tres en todo
el centro. Activa **Doble** para agrupar sesiones de esa asignatura en parejas.

Selecciona una fila, modifica los campos y pulsa **Editar** para cambiar un
recurso. Los nombres deben ser únicos dentro de su tipo. Al renombrar asignaturas
o profesores se actualizan sus asociaciones y restricciones; al eliminarlos se
retiran las referencias correspondientes. El horario ya generado conserva sus
nombres y configuración originales hasta que generes otro.

Asocia cada profesor con las asignaturas que puede impartir. En las asociaciones
de aulas, escribe nombres existentes separados por comas. Una limitación con
una o más aulas permite únicamente esas aulas. Si no existe esa limitación, el
profesor puede utilizar cualquier aula, incluidas las que añadas más tarde.
Eliminar la última limitación de aulas vuelve a permitir todas.

Evita comas dentro de los nombres de aula si vas a editar sus asociaciones con
este formulario: ese campo utiliza la coma como separador. Los archivos JSON
sí pueden almacenar esos nombres sin dividirlos.

## Restricciones

- **Días bloqueados:** selecciona un profesor o asignatura, marca los días y aplica
  el bloqueo. Se aplica a todas las semanas; una nueva aplicación sustituye los
  días anteriores de ese recurso.
- **No consecutivas:** impide que dos asignaturas ocupen turnos sucesivos en la
  misma aula, en cualquier orden.
- **No paralelas:** impide que dos asignaturas distintas de una pareja coincidan
  en el mismo turno, incluso en aulas diferentes. Permite clases simultáneas de
  la misma asignatura con profesores diferentes.

Para quitar un bloqueo o pareja, selecciona su fila y pulsa Eliminar. Una lista
vacía no añade restricciones. Las reglas completas, incluidos los límites de
repetición diaria, se describen en [Planificación](03-planificacion.md).

## Generar y consultar

Pulsa **Generar horario**. La aplicación muestra el resultado en la pestaña
Horario. Usa el selector de semana o las flechas para navegar. Las cabeceras
separan los días y las columnas corresponden a las aulas. La merienda se muestra
en una celda común que abarca todas las aulas.

Haz doble clic en una clase para resaltar todas las clases de su asignatura,
aunque cambie el profesor. El resaltado se conserva al cambiar de semana. La
información de selección cuenta sesiones de todas las aulas, tanto en la semana
visible como en el ciclo. La nota amarilla añade las restricciones de la
asignatura y de sus profesores, usando la configuración del horario generado.

Para quitar el resaltado, pulsa Escape, **Quitar resaltado** o haz clic en una
celda sin clase, una pausa o una cabecera. Usa las barras de desplazamiento para
recorrer aulas y días; el horario admite también rueda y Shift + rueda horizontal.

## Guardar, cargar y exportar

| Menú Archivo | Resultado |
| --- | --- |
| Guardar / ⌘S | Abre un selector de destino y escribe configuración y horario opcional. |
| Cargar / ⌘O | Abre un JSON actual o antiguo y recupera sus datos. |
| Exportar PDF | Escribe el último horario generado o cargado, con un día por página. |
| Limpiar | Restablece un centro vacío con los valores iniciales. |
| Salir / ⌘Q | Cierra la aplicación. |

Guardar permite elegir un nombre diferente cada vez. Cargar un documento con
horario no vuelve a ejecutar el planificador. Cargar solo una configuración
retira de la pantalla el horario que hubiera abierto anteriormente.

El PDF es A4 horizontal. Incluye curso, semana y día; los días especialmente
largos se reducen para caber en una sola página. No se exporta el resaltado
interactivo ni la nota de restricciones.

No hay guardado automático ni aviso de cambios pendientes al cargar, limpiar o
salir. Guarda antes de esas acciones si quieres conservar las modificaciones.
Limpiar no borra archivos del disco.

## Resolver problemas

| Situación | Comprobación |
| --- | --- |
| «No hay profesor elegible» | Verifica asignatura habilitada y aulas permitidas para ese profesor. |
| No se encuentra una planificación | Revisa frecuencias, turnos, días bloqueados, repetición diaria y disponibilidad de profesores. |
| Se agota la búsqueda | El límite es 10 segundos; vuelve a intentar o simplifica las restricciones. Esto no demuestra imposibilidad. |
| Aparece tiempo libre | No cabe una clase completa antes de la pausa; revisa inicio, duración y cambios. |
| El PDF conserva nombres u horas anteriores | Exporta el horario existente. Genera otro para aplicar la configuración editada. |
| Un archivo antiguo abre a otra hora | Se respetan sus horas explícitas; los nuevos valores por defecto no sustituyen datos guardados. |
| Un JSON se rechaza | Comprueba versión, referencias, nombres únicos, días válidos y franjas no solapadas. |
| La aplicación tarda al generar | La resolución se ejecuta en el hilo de la interfaz; durante la búsqueda puede no responder. |

Los archivos guardados contienen los nombres y horarios tal como se introducen.
Son documentos locales legibles, sin cifrado propio de la aplicación.
