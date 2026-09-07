# Desarrollo, API y mantenimiento

[← Formatos](04-formatos.md) · [Inicio](../README.md) · [Revisión →](06-revision.md)

## Entorno de trabajo

`pyproject.toml` define un paquete con distribución `src`, Python mínimo 3.11 y
setuptools como backend. Las dependencias de ejecución son OR-Tools y ReportLab;
Tkinter debe estar disponible en el intérprete. El extra `dev` añade pytest y Ruff.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

La instalación editable refleja los cambios en `src` al volver a ejecutar el
programa. Los mínimos declarados no constituyen un archivo de versiones fijadas.
Si cambias de intérprete o arquitectura, reconstruye el entorno virtual con ese
intérprete; no reutilices sus binarios como si fueran portables.

## Puntos de entrada

| Entrada | Comportamiento |
| --- | --- |
| `./run_app.sh` | Localiza el proyecto, prepara `.venv` si falta y ejecuta la aplicación. |
| `.venv/bin/scholar-calendar` | Abre `CalendarApp` con un centro vacío. |
| `.venv/bin/scholar-calendar-example` | Genera el ejemplo Python e imprime sus clases en la terminal. |
| `CalendarApp(config_path=None)` | Constructor Python; el argumento opcional admite un documento o configuración para cargar. |

El comando de escritorio no implementa argumentos CLI para elegir archivo.
Para automatizar tareas usa la API que sigue. El script de ejecución verifica
que estén el comando instalado y las importaciones de las dependencias antes de
volver a instalar; no actualiza automáticamente versiones ya instaladas.

## Modelos Python

Las siguientes clases son dataclasses congeladas. Se sustituyen con
`dataclasses.replace`; los mapas internos siguen requiriendo copias antes de
mutarlos.

| Clase | Campos |
| --- | --- |
| `Subject` | `name: str`, `lessons_per_cycle: int`, `double_period: bool = False`. La frecuencia es semanal. |
| `Teacher` | `name: str`. |
| `Classroom` | `name: str`. |
| `PlanningSlot` | `week`, `day`, `period` enteros; `start`, `end` de tipo `datetime.time`. |
| `ScheduledLesson` | `week`, `day`, `period`, `classroom`, `subject`, `teacher`, `start`, `end`. Las horas son texto `HH:MM`. |
| `Schedule` | `lessons: tuple[ScheduledLesson, ...]`. |
| `CalendarProject` | `planning`, `schedule_planning=None`, `schedule=None`. Si existe un horario al guardar, debe tener su configuración original. |

`PlanningInput` reúne:

| Campos | Contrato |
| --- | --- |
| `weeks` | Cantidad de semanas. |
| `subjects`, `teachers`, `classrooms`, `slots` | Tuplas de los modelos anteriores. |
| `teacher_subjects`, `teacher_classrooms` | Diccionarios de nombres a `frozenset[str]`. |
| `forbidden_consecutive`, `forbidden_parallel` | `frozenset[frozenset[str]]`; cada conjunto interior es una pareja. |
| `course_name` | Texto, inicialmente vacío. |
| `day_period_counts` | Mapa de días a turnos, o `None`. |
| `saturday_weeks` | `frozenset[int]`, inicialmente vacío. |
| `period_duration_minutes`, `transition_minutes` | 45 y 5 por defecto. |
| `class_start` | `08:30` por defecto. |
| `break_start`, `break_end` | `10:05` y `10:25`; admiten `None`. |
| `lunch_start`, `lunch_end` | `None` en el constructor del modelo. |
| `lunch_after_period` | 6 por defecto. |
| `teacher_unavailable_days`, `subject_unavailable_days` | Mapas a `frozenset[int]`, o `None`. |

**El constructor básico y los valores de la aplicación no son idénticos.** Para
obtener un centro con los valores que ve el usuario, llama a
`defaults.default_planning()`: añade comida 13:40–15:00, un ciclo de una semana,
seis turnos de lunes a viernes y mapas vacíos. Cada llamada construye una
configuración nueva sin recursos.

## Funciones de dominio

| Función | Uso |
| --- | --- |
| `clock.minutes_since_midnight(value)` | Convierte una hora en minutos desde medianoche. |
| `clock.parse_optional_time(value)` | Lee una hora del formulario; texto vacío produce `None`. |
| `models.build_daily_periods(...)` | Devuelve una tupla de pares `(inicio, fin)` aplicando el reloj. |
| `models.build_slots(...)` | Repite los intervalos por semanas y días y aplica turnos y sábados. |
| `validation.validate_planning(planning)` | Valida estructura; devuelve `None` o lanza `ValueError`. |
| `solver.solve(planning)` | Devuelve `Schedule`; puede lanzar `ValueError` o `ScheduleError`. |
| `timeline.daily_rows(planning, week, day)` | Devuelve `tuple[TimelineRow, ...]` para un día. |
| `subject_details.subject_restrictions(planning, schedule, subject_name)` | Devuelve las líneas de restricciones de esa asignatura. |

Firma de construcción de intervalos, con argumentos exclusivamente por nombre:

```python
build_daily_periods(
    period_count=6,
    duration_minutes=45,
    transition_minutes=5,
    start=time(8, 30),
    break_start=time(10, 5),
    break_end=time(10, 25),
    lunch_start=None,
    lunch_end=None,
    lunch_after_period=6,
)
```

`build_slots(weeks=..., days=..., daily_periods=...,
day_period_counts=None, saturday_weeks=frozenset())` devuelve franjas en orden
semana/día/turno. Un mapa de turnos limita los intervalos de cada día; el sábado
requiere pertenecer a `saturday_weeks`. No inventa intervalos si el mapa pide más
que los recibidos: el llamador debe construir suficientes `daily_periods`.

`TimelineRow` contiene `start`, `end`, `label` y `period=None` para las pausas.
Su propiedad `hours` produce `HH:MM – HH:MM`.

## Funciones de archivo y PDF

| Función | Resultado o efecto |
| --- | --- |
| `config.load_planning(path)` | Lee una configuración independiente. No reconoce envolturas de proyecto. |
| `config.planning_from_dict(data)` | Convierte un diccionario en `PlanningInput` y lo valida. |
| `config.planning_to_dict(planning, include_slots=False)` | Produce un diccionario; no escribe ni valida por sí sola. |
| `config.save_planning(planning, path)` | Valida y guarda una configuración independiente con franjas exactas. |
| `project_file.load_project(path)` | Devuelve `CalendarProject`, aceptando los tres formatos. |
| `project_file.save_project(project, path)` | Guarda el documento completo mediante escritura atómica. |
| `schedule_file.load_schedule(path)` | Lee exclusivamente un archivo histórico de horario; devuelve `(planning, schedule)`. |
| `schedule_file.save_schedule(planning, schedule, path)` | Escribe ese formato histórico. |
| `schedule_file.schedule_from_dict(data)` / `schedule_to_dict(planning, schedule)` | Conversión del bloque de horario, con validación de su estructura. |
| `storage.write_json(data, path)` | Escritura atómica reutilizable; no crea directorios padre. |
| `pdf.export_schedule_pdf(planning, schedule, path)` | Exporta el horario; usa la configuración con la que se generó. |

Las funciones de alto nivel aceptan `str` o `pathlib.Path`. Los errores de disco
propagan `OSError`. Los lectores de bajo nivel pueden propagar también errores
de estructura JSON; `load_project()` los normaliza a `ValueError` para la interfaz.
No se debe cargar una envoltura de proyecto con `load_planning()`.

## Ejemplo completo sin interfaz

Ejecuta desde la raíz del proyecto con su Python. Se crean archivos en `salida`:

```python
from pathlib import Path

from scholar_calendar.config import load_planning
from scholar_calendar.pdf import export_schedule_pdf
from scholar_calendar.project_file import CalendarProject, load_project, save_project
from scholar_calendar.solver import solve

planning = load_planning("examples/minimal.json")
schedule = solve(planning)

output = Path("salida")
output.mkdir(exist_ok=True)
path = output / "centro.json"
save_project(CalendarProject(planning, planning, schedule), path)

restored = load_project(path)
assert restored.schedule == schedule
assert restored.schedule_planning is not None
assert restored.schedule is not None
export_schedule_pdf(restored.schedule_planning, restored.schedule, output / "horario.pdf")
print(f"{len(restored.schedule.lessons)} sesiones recuperadas")
```

El resultado tiene cinco sesiones. Para crear una configuración propia sin
archivo inicial:

```python
from dataclasses import replace

from scholar_calendar.defaults import default_planning
from scholar_calendar.models import Classroom, Subject, Teacher
from scholar_calendar.solver import solve

planning = replace(
    default_planning(),
    course_name="Mi centro",
    subjects=(Subject("Historia", 2),),
    teachers=(Teacher("Ana"),),
    classrooms=(Classroom("Grupo A"),),
    teacher_subjects={"Ana": frozenset({"Historia"})},
)
schedule = solve(planning)
assert len(schedule.lessons) == 2
```

## Pruebas y herramientas

```sh
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/python -m pytest
```

La comprobación sin sesión gráfica omite `test_schedule_ui.py`. Para incluirla:

```sh
SCHOLAR_CALENDAR_GUI_TESTS=1 .venv/bin/python -m pytest
```

Estas pruebas abren ventanas reales. No ejecutes simultáneamente capturas visuales
y otra suite GUI: las ventanas pueden taparse o competir por el foco. En un
entorno restringido se necesita acceso a la sesión gráfica para crear Tk.

| Archivo de pruebas | Comportamiento cubierto |
| --- | --- |
| `test_clock.py` | Alineación de clases, pausas, huecos y validación del reloj. |
| `test_calendar_config.py` | Configuración, intervalos explícitos, sábados y compatibilidad. |
| `test_solver.py` | Frecuencias, dobles, días bloqueados, incompatibilidades y tiempo agotado. |
| `test_project_file.py` | Documento unificado, ciclos irregulares y rechazo de configuraciones inválidas. |
| `test_schedule_file.py` | Horarios históricos, asignaciones exactas, corrupción y fallo de escritura. |
| `test_schedule_ui.py` | Diálogos, cancelación, menú, selección, renombrado, guardado y limpieza. |
| `test_configuration_overview.py` | Resumen completo de recursos y restricciones. |
| `test_subject_details.py` | Restricciones de asignatura y profesores mostradas en la nota. |
| `test_pdf.py` | Una página por día incluso en jornadas largas. |

Prueba invariantes y resultados, no una distribución exacta del solver, salvo
cuando estés comprobando la recuperación de un horario ya guardado. La búsqueda
puede elegir soluciones diferentes igualmente válidas.

## Cambiar el proyecto con coherencia

- **Nueva restricción:** define su representación y validación, añade el editor,
  el resumen y la nota, implementa la condición en `solver.py` y documenta su
  semántica y serialización. Añade un caso que permita distinguirla de otra regla.
- **Nuevo valor del reloj:** revisa modelo, configuración, valores iniciales y
  variables del formulario. Mantén las firmas de reloj y ciclo al día para no
  reconstruir accidentalmente archivos importados.
- **Cambio visual:** modifica primero `theme.py` o el componente correspondiente.
  Comprueba ventana mínima de 980 × 650, diálogos, textos largos, foco por teclado,
  botones desactivados y desplazamiento. Conserva los bindings de ttk.
- **Cambio de formato incompatible:** aumenta la versión y define explícitamente
  su lectura/migración. Los campos opcionales nuevos deben tener un comportamiento
  definido cuando falten.
- **Refactor del estado:** conserva la separación entre configuración editable y
  configuración del horario. Cancelar un diálogo debe ser reversible.

Los estilos usan imágenes Tk generadas en código, sin librerías gráficas
adicionales. Conserva sus referencias y evita imágenes de relleno de un solo
píxel en superficies grandes: el mosaico puede ralentizar mucho Tk en macOS.

## Límites de las comprobaciones

La validación estructural no demuestra que el problema tenga solución. Las
pruebas de interfaz no cubren todas las resoluciones, monitores ni sistemas
operativos; los atajos y las comprobaciones visuales están orientados a macOS.
El PDF utiliza Helvetica estándar, por lo que símbolos fuera de su repertorio
pueden necesitar otra fuente si se amplía el uso a otros alfabetos.
