# Scholar Calendar

Aplicación de escritorio para planificar horarios escolares con restricciones configurables.
Python 3.11 o posterior, Tkinter, OR-Tools y ReportLab.

## Inicio rápido

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/scholar-calendar
```

También puedes iniciar la aplicación con `./run_app.sh`. El script crea el entorno
e instala las dependencias cuando faltan; los siguientes inicios abren la aplicación
sin reinstalar el paquete.
La aplicación abre una configuración vacía. Usa **Archivo → Cargar** para
cargar `examples/cycle.json` o una definición guardada anteriormente.

## Interfaz

La cabecera compacta reúne el menú Archivo y la generación del horario. Los
controles usan tarjetas y botones redondeados, separadores suaves y estados
visibles de foco y selección. Las acciones de eliminar se distinguen en rojo suave.

- **Configuración del centro:** una vista general con toda la jornada, los días
  lectivos, las asignaturas, los profesores, las aulas y las restricciones.
  Muestra los valores y las relaciones completos, con desplazamiento vertical.
  Los botones **Editar**, **Asociaciones** y **Días bloqueados** abren diálogos
  específicos para modificar cada sección.
- **Horario:** navegación entre semanas, cabeceras destacadas por día y filas
  identificadas con el día y el turno. Las pausas y los tiempos libres tienen
  colores propios. La tabla permite desplazarse horizontalmente entre aulas.

En los diálogos, **Guardar cambios** aplica la edición y actualiza la vista general.
**Cancelar**, Escape o cerrar la ventana descarta lo editado, incluidas altas,
bajas y cambios en asociaciones. Los datos inválidos mantienen el diálogo abierto
para corregirlos. Para conservar la configuración en disco, usa después
**Archivo → Guardar** en la ventana principal. Los diálogos se abren centrados
en la pantalla.

**Generar horario** calcula la distribución. **Archivo → Exportar PDF** exporta
el último horario generado, con
una hoja por día y el curso y la semana identificados en cada hoja. Las jornadas
largas se reducen de escala para caber completas en su página.
Los cambios de configuración requieren generar de nuevo para actualizar el horario.

## Menú Archivo

- **Guardar** (⌘S): conserva la configuración actual y, si existe, el horario
  generado en un único archivo JSON. Si has editado la configuración después de
  generar, se guardan también esos cambios y la configuración original del horario.
  Puedes guardar distintas versiones con nombres diferentes.
- **Cargar** (⌘O): recupera el documento sin recalcular el horario. También acepta
  los antiguos archivos de configuración y los archivos `.horario.json`.
- **Exportar PDF**: disponible cuando hay un horario generado o cargado.
- **Limpiar**: vacía asignaturas, profesores, aulas, asociaciones, restricciones
  y horario; restablece la jornada y los demás valores por defecto. No borra
  los archivos guardados.
- **Salir** (⌘Q): cierra la aplicación.

El menú está disponible tanto en la ventana como en la barra de menús de macOS.

## Ver la distribución de una asignatura

Haz **doble clic en una celda de clase**: se resaltan en amarillo todas las celdas
de esa asignatura, en cualquier aula y con cualquier profesor. El resaltado se
mantiene al cambiar de semana, y se indica el número de sesiones de la semana
visible y del ciclo completo.

La selección muestra una nota de fondo amarillo crema y borde discontinuo con
sus restricciones: frecuencia por aula, turnos dobles, días bloqueados,
asignaturas incompatibles y limitaciones de días o aulas de sus profesores.
También se identifican los profesores habilitados que no tienen clases de esa
asignatura en el ciclo. La nota utiliza la configuración del horario generado o
cargado y permite desplazarse si la lista es larga.

Para quitarlo, pulsa **Escape**, usa **Quitar resaltado** o haz clic en una celda
vacía, una pausa o una cabecera de día. Un doble clic en otra asignatura cambia
el resaltado a esa asignatura.

## Reloj escolar

El inicio por defecto es **08:30**; se puede ajustar en formato `HH:MM` y se
guarda en `clock.start`. La merienda es de **10:05 a 10:25** y la comida
por defecto es de **13:40 a 15:00**.
La vista previa se actualiza al editar el reloj y muestra el día con más turnos,
incluyendo cambios de clase, merienda, comida y tiempo libre. La vista general
muestra estas franjas en una tabla con actividad, horario y duración.

Las clases conservan su duración y no invaden las pausas. Por ejemplo, con inicio
08:00, turnos de 45 minutos y cambios de 5 minutos, los dos primeros turnos
terminan a las 09:35. Tras el cambio quedan 25 minutos libres hasta la merienda
10:05–10:25: no cabe otro turno completo. Con inicio **08:30**, el segundo turno
termina a las **10:05** y el tercero empieza a las **10:25**.

Para desactivar una pausa, deja vacíos sus dos campos. Si hay comida después de
un turno concreto, el siguiente comienza como mínimo al finalizar la comida;
el reloj nunca retrocede si esa hora ya pasó. Se rechazan duraciones inválidas,
pausas incompletas o solapadas y jornadas que llegan a medianoche.

Los intervalos explícitos de un JSON antiguo se conservan al cargarlo, guardarlo
o generar el horario. Si cambias el reloj o necesitas más turnos que los definidos,
se recalculan con los valores del formulario.

## Reglas de planificación

- Cada asignatura tiene una frecuencia **semanal por aula**, que se cumple en
  cada semana del ciclo, no solo en el total acumulado.
- Un aula y un profesor solo pueden tener una clase en cada franja.
- Los profesores deben estar asociados a las asignaturas que imparten. Una lista
  de aulas vacía o ausente permite al profesor utilizar cualquier aula.
- Las asignaturas normales aparecen como máximo una vez al día en cada aula.
- Las asignaturas con doble turno se agrupan en parejas de turnos consecutivos,
  con como máximo una sesión suelta por semana si la frecuencia es impar.
- Se permiten distintos números de turnos de lunes a sábado. El sábado se activa
  por semana; el domingo no se utiliza.
- Se pueden bloquear días para profesores y asignaturas, y definir parejas
  incompatibles en turnos consecutivos o simultáneos.

## Persistencia y estructura

La configuración y el horario generado opcional se guardan en un único documento
JSON. Los documentos incluyen una versión de formato y se guardan mediante
reemplazo atómico para conservar el archivo anterior si falla la escritura.
Aún no hay base de datos, histórico automático ni exportación ICS.

El JSON usa `lessons_per_week`. Por compatibilidad también se acepta el antiguo
`lessons_per_cycle`, interpretado como frecuencia semanal; el atributo Python
conserva ese nombre histórico.

Las restricciones opcionales se representan con listas u objetos vacíos.
Por ejemplo, `"teacher_unavailable_days": {"Profesor 1": [3, 5]}` bloquea miércoles
y viernes. Los días usan `1` para lunes y `6` para sábado.

- `models.py`: modelo de datos y construcción de franjas horarias.
- `clock.py`: funciones compartidas para interpretar horas y calcular minutos.
- `config.py`: lectura y escritura de configuraciones.
- `solver.py`: restricciones y resolución con OR-Tools CP-SAT.
- `timeline.py`: desglose de clases, cambios, pausas y tiempos libres.
- `desktop.py`: interfaz Tkinter.
- `configuration_overview.py`: resumen completo de la configuración y acceso a sus editores.
- `theme.py`: paleta y estilos de la interfaz.
- `schedule_grid.py`: cuadrícula con resaltado por asignatura a nivel de celda.
- `subject_details.py`: restricciones relevantes de la asignatura y sus profesores.
- `restriction_note.py`: nota visual de la selección, con desplazamiento propio.
- `project_file.py`: documentos de configuración con horario opcional y lectura de formatos antiguos.
- `schedule_file.py`: serialización de horarios completos y escritura atómica.
- `pdf.py`: exportación del horario a PDF.

El ejemplo de consola se ejecuta con `.venv/bin/scholar-calendar-example`.

Las pruebas de interfaz requieren una sesión de escritorio y se activan con
`SCHOLAR_CALENDAR_GUI_TESTS=1 .venv/bin/python -m pytest`.

## Mantenimiento del código

Las dependencias de desarrollo se instalan con
`.venv/bin/python -m pip install -e '.[dev]'`.

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/python -m pytest
```

Usa `.venv/bin/ruff format src tests` para aplicar el formato común. Las reglas
del analizador y del formateador se definen en `pyproject.toml`.
