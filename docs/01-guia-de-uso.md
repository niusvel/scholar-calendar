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
verticalmente. El recorrido empieza por **1. Aulas / grupos**, continúa con
**2. Asignaturas** y termina con **3. Profesores**. Debajo puedes ajustar la
jornada y los días lectivos. Cada apartado tiene un único botón **Configurar**.

| Apartado | Contenido del editor |
| --- | --- |
| Aulas / grupos | Creación, cambio de nombres y eliminación de grupos. |
| Asignaturas | Pestañas **Asignaturas y aulas** (frecuencia y dobles), **Disponibilidad** e **Incompatibilidades**. |
| Profesores | Pestañas **Profesores**, **Asignaturas y aulas**, **Aulas generales** y **Disponibilidad**. |
| Jornada escolar / Días lectivos | Curso, semanas, reloj, turnos por día, sábados y vista previa. |

Las pestañas que necesitan recursos se habilitan cuando estos existen. Por
ejemplo, para asociar un profesor con una asignatura y sus aulas deben haberse
creado los tres recursos. Seleccionar una asignatura o profesor facilita pasar
a sus formularios asociados con ese recurso ya elegido. Cada tipo tiene su
propia selección de días, para no mezclar bloqueos.

En cualquier diálogo, **Guardar cambios** aplica la edición a la configuración
en memoria. **Cancelar**, Escape o cerrar ese diálogo descarta todos los cambios
de esa edición, incluso altas y bajas. Para conservarlos en disco utiliza después
**Menú ☰ → Guardar**. Los errores de validación mantienen abierto el editor.
Las operaciones del menú ☰ se desactivan mientras se edita.

## Jornada y reloj

| Valor inicial | Configuración |
| --- | --- |
| Ciclo | 1 semana |
| Lunes a viernes | 6 turnos por día |
| Sábado | 0 turnos, sin semanas activadas |
| Inicio | 07:40 |
| Clase | 45 minutos |
| Cambio | 5 minutos |
| Merienda | 10:05–10:25 |
| Comida | 13:40–15:00, después del turno 6 |

Introduce horas en formato `HH:MM`. Para quitar una pausa, vacía tanto su inicio
como su final. Para habilitar un sábado, indica sus turnos y marca las semanas en
las que se utiliza. Un domingo nunca se incluye.

La tabla de franjas muestra actividades, horas y duración. Los tres primeros
turnos iniciales son 07:40–08:25, 08:30–09:15 y 09:20–10:05; tras la merienda,
el cuarto empieza a las 10:25. No se recortan clases para hacerlas caber antes de una pausa.

La comida no añade turnos: con seis turnos la jornada termina a las 12:50. Si
habilitas un séptimo, comienza como mínimo a las 15:00. La vista del horario
muestra pausas entre clases; no añade una fila de comida después de la última
clase. Consulta [el cálculo del reloj](03-planificacion.md#el-reloj-escolar) para
entender los huecos y las pausas.

## Recursos y asociaciones

Añade asignaturas con una frecuencia entera positiva. Por ejemplo, «Matemáticas,
3 sesiones» significa tres sesiones por semana en **cada aula**, no tres en todo
el centro. Activa **Doble** para agrupar sesiones de esa asignatura en parejas.
Por defecto se aplica en todas las aulas. Para limitarlo, desmarca **Todas las
aulas / grupos** en **Aplicar turnos dobles en** y selecciona las aulas con un
clic en cada una. En las demás, la asignatura tendrá como máximo una sesión
diaria. Pulsa **Añadir** o **Editar** y después **Guardar cambios**.

Selecciona una fila, modifica los campos y pulsa **Editar** para cambiar un
recurso. Los nombres deben ser únicos dentro de su tipo. Al renombrar asignaturas
o profesores se actualizan sus asociaciones y restricciones; al eliminarlos se
retiran las referencias correspondientes. Si únicamente cambias nombres de asignaturas, profesores o aulas, se actualizan
en el horario ya generado al guardar los cambios del diálogo, sin mover clases.
También se actualizan el resaltado, las referencias y la exportación PDF. El
nombre del curso se puede actualizar sin generar de nuevo.

En **Profesores → Configurar → Asignaturas y aulas**, selecciona un profesor y una asignatura. El selector permite
dejar **Todas las aulas / grupos** o elegir varias aulas para esa pareja. Pulsa
**Vincular** para añadirla o **Editar** para modificar la fila seleccionada, y
después **Guardar cambios**. Por ejemplo, Ana puede tener Matemáticas en 1.º y
Lengua en 2.º. Seleccionar otra pareja recupera sus aulas guardadas.

Estas restricciones se suman a las generales de **Profesores → Aulas generales**: si hay dos
límites, solo se permiten las aulas presentes en ambos. Las asociaciones antiguas
mantienen su comportamiento hasta que les añadas un límite específico.

En las asociaciones generales de aulas, escribe nombres existentes separados por comas. Una limitación con
una o más aulas permite únicamente esas aulas. Si no existe esa limitación, el
profesor puede utilizar cualquier aula, incluidas las que añadas más tarde.
Eliminar la última limitación de aulas vuelve a permitir todas.

Los nuevos selectores distinguen **Todas** de una selección vacía: si desmarcas
**Todas** y no seleccionas aulas, la pareja no podrá impartir clases en ninguna,
o la asignatura no usará dobles en ninguna, según el selector. Al eliminar la
última aula de una selección específica se conserva ese límite vacío. Para
permitir todas, marca **Todas** expresamente. Al renombrar aulas, asignaturas o
profesores, se actualizan sus selecciones y asociaciones.

Evita comas dentro de los nombres de aula si vas a editar sus asociaciones
generales con el campo de texto: utiliza la coma como separador. Los nuevos
selectores por asignatura y los archivos JSON admiten esos nombres completos.

## Restricciones

Los bloqueos de días y turnos se editan en la pestaña **Disponibilidad**, dentro
de **Asignaturas** o **Profesores**. Las
parejas incompatibles se configuran en **Asignaturas → Incompatibilidades**.

- **Días y turnos bloqueados:** selecciona el recurso, marca uno o varios días y
  elige **Todo el día** o un número de turno. Pulsa **Añadir bloqueo**. Los bloqueos
  se suman; para cambiarlos, selecciona una fila y pulsa **Actualizar seleccionado**.
  **Eliminar seleccionado** retira solo esa fila.
- **Profesor al impartir una asignatura:** en **Profesores → Disponibilidad**, el
  campo **Cuando imparte** permite escoger una asignatura asociada o **Todas las
  asignaturas**. Para el ejemplo «A no imparte B el martes en el turno 4», elige
  A, B, Martes y 4, añade el bloqueo y pulsa **Guardar cambios**. Otros profesores
  pueden impartir B en ese turno, y A puede impartir otras asignaturas.
- **Aula específica:** el campo **Aula / grupo** limita el bloqueo al aula elegida;
  **Todas las aulas** mantiene el alcance general. Está disponible tanto para
  profesores como para asignaturas. Para bloquear A–B en C los lunes y martes
  en los turnos 4 y 5, selecciona A, B, C y ambos días; añade el turno 4 y luego
  el 5. A continuación, deja marcado solo el jueves y añade el turno 5.
  Se crearán cinco filas; el jueves seguirá disponible el turno 4 en C.
- **No consecutivas:** impide que dos asignaturas ocupen turnos sucesivos en la
  misma aula, en cualquier orden.
- **No paralelas:** impide que dos asignaturas distintas de una pareja coincidan
  en el mismo turno, incluso en aulas diferentes. Permite clases simultáneas de
  la misma asignatura con profesores diferentes.

Un bloqueo de asignatura afecta a todos sus profesores; uno general de profesor
abarca todas sus asignaturas. Los bloqueos de ambos y los de pareja se acumulan,
son obligatorios y se repiten en todas las semanas, dentro del aula indicada
o en todas si no se limita el aula. Para varios turnos,
añade un bloqueo por turno. El número identifica el turno de clase, sin contar
merienda, comida o cambios. Si cambia su hora, el bloqueo sigue a ese número.
Los turnos que no existan en un día no producen ningún efecto hasta que existan.

Los bloqueos antiguos por día completo se cargan como **Todo el día**. Renombrar
recursos mantiene sus bloqueos; eliminar una asociación retira únicamente los de
esa pareja. Eliminar un aula retira sus bloqueos específicos y conserva los
generales. Cambiar los bloqueos requiere generar un nuevo horario.

Para quitar un bloqueo o pareja, selecciona su fila y pulsa Eliminar. Una lista
vacía no añade restricciones. Las reglas completas, incluidos los límites de
repetición diaria, se describen en [Planificación](03-planificacion.md).

## Preferencias de generación

El generador intenta cumplir también dos preferencias no obligatorias:

- Que cada asignatura tenga al menos una sesión fuera de los turnos 5.º y 6.º,
  en cada aula y semana. No prohíbe utilizar esos turnos.
- Que la merienda no quede entre las dos sesiones de un doble. Se usa la hora
  configurada de merienda, aunque se haya cambiado respecto al valor inicial.

Las dos tienen el mismo peso. Si no se pueden cumplir a la vez, se busca reducir
el total de incumplimientos. Nunca se eliminan clases ni se incumplen reglas
obligatorias para cumplir estas preferencias. Se aplican al generar, no al cargar
un horario existente.

## Cuándo hay que generar otro horario

Cambiar frecuencias, marcas de doble, asociaciones, días bloqueados, parejas
incompatibles, recursos, reloj o estructura del ciclo requiere una nueva
asignación. Aparece un aviso amarillo visible desde ambas pestañas, con el botón
**Generar de nuevo**. El horario anterior sigue disponible para consulta y PDF,
pero no representa la configuración editada.

El aviso se mantiene al guardar y volver a cargar, y si falla la nueva generación.
Desaparece cuando se genera correctamente o se restauran los valores con los que
se calculó el horario. Limpiar retira tanto el horario como el aviso.

Si una misma edición mezcla un renombrado con cambios de generación, el horario
anterior conserva sus nombres hasta regenerar. Si ya había cambios pendientes,
un renombrado no los resuelve. No se deducen identidades por la posición de los
recursos en archivos editados externamente.

## Generar y consultar

Si la configuración es incompatible, se abre una ventana centrada con las
condiciones que no pueden cumplirse juntas. Indica asignaturas, profesores,
aulas, semanas, frecuencias y bloqueos implicados, según el conflicto, y muestra
qué sección debes revisar. **Revisar configuración** vuelve a la pantalla de
configuración. La lista tiene desplazamiento y no modifica ningún dato.

Por ejemplo, puede señalar que Matemáticas requiere tres sesiones, que solo hay
dos turnos en esa semana, o que un bloqueo de Ana impide impartirla en un aula.
También identifica profesores compartidos, límites diarios, dobles e
incompatibilidades. Si no hay profesor elegible, distingue entre falta de
asociación y restricciones de aulas de los profesores asociados.

Las condiciones se deben evaluar juntas: no significa que cada una esté mal por
separado. Puede haber otros conflictos independientes; tras corregir la
configuración, vuelve a generar. Las preferencias opcionales no impiden generar.
El horario anterior se conserva si el intento falla.

La búsqueda del horario dispone de diez segundos. Si demuestra imposibilidad,
se realiza un diagnóstico adicional con hasta diez segundos de búsqueda. Si no
consigue aislar la causa en ese plazo, lo indica sin inventarla. Agotar el tiempo
de generación sin encontrar solución no demuestra que el horario sea imposible.

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

El botón con el icono ☰, a la izquierda de la cabecera, abre el menú.

| Menú ☰ | Resultado |
| --- | --- |
| Guardar / ⌘S | Abre un selector de destino y escribe configuración y horario opcional. |
| Cargar / ⌘O | Abre un JSON actual o antiguo y recupera sus datos. |
| Limpiar | Restablece un centro vacío con los valores iniciales. |
| Reglas de generación | Abre una ventana centrada con las reglas obligatorias, dinámicas y opcionales. |
| Salir / ⌘Q | Cierra la aplicación. |

Guardar y Cargar abren un selector centrado con el estilo de la aplicación.
Puedes navegar por carpetas con doble clic, **Subir**, las ubicaciones rápidas
o escribiendo una ruta y pulsando **Ir**. El buscador filtra por nombre y se
muestran las carpetas y los archivos JSON. Al seleccionar un archivo para cargar,
se muestra el curso, los recursos y si contiene un horario; un archivo inválido
no habilita **Cargar**. Se abre inicialmente en la carpeta del proyecto actual,
o en la carpeta de trabajo si todavía no hay uno.

Al guardar, escribe el nombre: se añade `.json` si hace falta. Se pide confirmación
antes de reemplazar un archivo existente. **Cancelar**, Escape o cerrar el
selector no cambia los datos ni escribe archivos.

Guardar permite elegir un nombre diferente cada vez. Cargar un documento con
horario no vuelve a ejecutar el planificador. Cargar solo una configuración
retira de la pantalla el horario que hubiera abierto anteriormente.

El botón **Exportar PDF**, junto a **Generar horario**, se habilita cuando hay un
horario generado o cargado. Exporta un día por página.

El PDF es A4 horizontal. Incluye curso, semana y día; los días especialmente
largos se reducen para caber en una sola página. No se exporta el resaltado
interactivo ni la nota de restricciones.

Para exportar la explicación del motor, abre **Menú ☰ → Reglas de generación**
y pulsa **Exportar PDF** en esa ventana. Incluye las tres categorías completas,
independientemente de la pestaña seleccionada, en A4 vertical con páginas numeradas.
Esta exportación está disponible aunque todavía no hayas generado un horario.

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
| El PDF conserva datos anteriores | Revisa si hay un aviso de regeneración: exporta el horario existente. Los cambios únicamente de nombres sí se aplican sin regenerar. |
| Un archivo antiguo abre a otra hora | Se respetan sus horas explícitas; los nuevos valores por defecto no sustituyen datos guardados. |
| Un JSON se rechaza | Comprueba versión, referencias, nombres únicos, días válidos y franjas no solapadas. |
| La aplicación tarda al generar | La resolución se ejecuta en el hilo de la interfaz; durante la búsqueda puede no responder. |

Los archivos guardados contienen los nombres y horarios tal como se introducen.
Son documentos locales legibles, sin cifrado propio de la aplicación.
