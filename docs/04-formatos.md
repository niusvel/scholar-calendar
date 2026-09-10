# Formatos de archivo y persistencia

[← Planificación](03-planificacion.md) · [Inicio](../README.md) · [Desarrollo y API →](05-desarrollo.md)

## Formato recomendado: documento del centro

**Menú ☰ → Guardar** utiliza un JSON UTF-8 con esta estructura:

```json
{
  "type": "scholar-calendar-project",
  "version": 1,
  "configuration": {},
  "generated": null
}
```

Este fragmento es un esquema de envoltura: `configuration` debe contener una
configuración válida, no un objeto vacío. Para un documento completo de partida,
carga [el ejemplo mínimo](../examples/minimal.json) y guárdalo desde la aplicación.

| Campo | Contenido |
| --- | --- |
| `type` | Literal `scholar-calendar-project`. |
| `version` | Entero `1`; una versión desconocida se rechaza. |
| `configuration` | Configuración actual, incluida la edición posterior a una generación. |
| `generated` | `null` si no hay horario; en otro caso, un objeto `scholar-calendar-schedule`. |

El bloque `generated` incluye su propia configuración. Puede diferir de
`configuration`: por ejemplo, puede haberse cambiado la frecuencia de una asignatura después de
generar. La duplicación permite conservar tanto los cambios pendientes de
regeneración como el horario que se está consultando.

## Configuración

Los siguientes campos pertenecen a `configuration` o a un archivo independiente
de configuración sin `type`.

| Campo | Tipo y significado | Si falta |
| --- | --- | --- |
| `weeks` | Entero de 1 a 52. | Obligatorio. |
| `subjects` | Lista de asignaturas. | Obligatorio; puede estar vacía. |
| `teachers` | Lista de objetos con `name`. | Obligatorio; puede estar vacía. |
| `classrooms` | Lista de objetos con `name`. | Obligatorio; puede estar vacía. |
| `teacher_subjects` | Objeto profesor → lista de asignaturas habilitadas. | Obligatorio; `{}` es válido. |
| `teacher_classrooms` | Objeto profesor → lista de aulas permitidas. | Obligatorio; `{}` permite todas las aulas. |
| `teacher_subject_classrooms` | Objeto profesor → asignatura → lista de aulas permitidas para esa pareja. | `{}`; no añade límites a los generales. |
| `course_name` | Texto identificativo del curso. | Cadena vacía. |
| `clock` | Parámetros del reloj. | Valores iniciales e inferencias descritos más abajo. |
| `daily_periods` | Lista de objetos `start` / `end`, sin día ni semana. | Se calculan con `clock`. |
| `day_period_counts` | Objeto día → número no negativo de turnos. Las claves JSON son texto. | Usa `days` y la cantidad de intervalos diarios. |
| `days` | Cantidad de días utilizada si no hay un mapa de turnos. | 5; se limita a lunes–sábado. |
| `saturday_weeks` | Lista de semanas del ciclo con sábado activo. | `[]`. |
| `teacher_unavailable_days` | Objeto profesor → lista de días bloqueados. | `{}`. |
| `subject_unavailable_days` | Objeto asignatura → lista de días bloqueados. | `{}`. |
| `availability_blocks` | Lista de bloqueos por día, turno, recurso o pareja y aula opcional. | `[]`. |
| `forbidden_consecutive` | Lista de parejas de asignaturas no consecutivas. | `[]`. |
| `forbidden_parallel` | Lista de parejas de asignaturas no simultáneas. | `[]`. |
| `slots` | Lista de franjas exactas por semana y día. | Reconstruye las franjas con los intervalos y el mapa de días. |

Un elemento de `subjects` contiene:

```json
{"name": "Laboratorio", "lessons_per_week": 2, "double_period": true}
```

`name` identifica el recurso y no puede estar vacío ni repetirse dentro de su
tipo. Las referencias deben coincidir exactamente, incluidas mayúsculas y tildes.
`lessons_per_week` es la frecuencia semanal por aula. Si falta, se acepta
`lessons_per_cycle` por compatibilidad; si faltan ambos se interpreta cero.
Si están presentes los dos, prevalece `lessons_per_week`.
`double_period` es un booleano y su valor inicial es `false`.

`double_classrooms` es opcional en cada asignatura. Omitido o `null`, aplica
el modo doble a todas las aulas cuando `double_period` es `true`. Una lista
lo limita a esas aulas; `[]` no aplica dobles en ninguna. Con `double_period=false`
no se aplica el modo doble, independientemente de la lista.

Ejemplo de asignatura doble únicamente en 1.º y límites distintos para Ana:

```json
{
  "subjects": [
    {"name": "Matemáticas", "lessons_per_week": 2, "double_period": true, "double_classrooms": ["1.º"]},
    {"name": "Lengua", "lessons_per_week": 2}
  ],
  "teacher_subjects": {"Ana": ["Matemáticas", "Lengua"]},
  "teacher_subject_classrooms": {
    "Ana": {"Matemáticas": ["1.º"], "Lengua": ["2.º"]}
  }
}
```

Este fragmento necesita el resto de la configuración, incluidos profesores y
aulas existentes. Los límites de pareja se intersectan con `teacher_classrooms`.
Una pareja ausente no añade restricciones; una lista vacía bloquea todas sus
aulas. Esto difiere de la lista general vacía, que conserva su significado
histórico de acceso sin limitación. Los nuevos campos se guardan tanto en la
configuración editable como en la copia del horario generado; los archivos
anteriores, que los omiten, conservan sus reglas originales.

Un bloqueo de `availability_blocks` tiene `day` (entero de 1 a 6), `period`
(entero positivo, o `null`/omitido para todo el día), `teacher`, `subject` y
`classroom` (nombre de un aula existente, o `null`/omitido para todas las aulas).
Al menos uno de los dos recursos debe estar indicado y existir; si están ambos,
debe existir su asociación. No se aceptan valores booleanos como día o turno.

```json
{
  "availability_blocks": [
    {"teacher": "A", "subject": "B", "classroom": "C", "day": 1, "period": 4},
    {"teacher": "A", "subject": "B", "classroom": "C", "day": 1, "period": 5},
    {"teacher": "A", "subject": "B", "classroom": "C", "day": 2, "period": 4},
    {"teacher": "A", "subject": "B", "classroom": "C", "day": 2, "period": 5},
    {"teacher": "A", "subject": "B", "classroom": "C", "day": 4, "period": 5},
    {"teacher": "A", "day": 3, "period": 1},
    {"subject": "B", "day": 5, "period": null}
  ]
}
```

El ejemplo bloquea A–B en C los lunes y martes en los turnos 4 y 5, y el jueves
solo en el turno 5. También bloquea A con cualquier asignatura el miércoles en
el turno 1, y B con cualquier profesor el viernes completo, estos dos en todas
las aulas. Los bloqueos se repiten cada semana y se suman a los mapas de días
históricos. Los documentos anteriores que omiten `classroom` mantienen el alcance
de todas las aulas; los que omiten `availability_blocks` conservan sus reglas.
La configuración editable y la copia del horario guardan sus propios bloqueos.

Las parejas deben contener dos asignaturas distintas y existentes. Su orden no
importa. Los días bloqueados admiten enteros de 1 a 6. Por compatibilidad,
`day_period_counts` ignora una entrada de domingo (`"7"`); esto no convierte el
domingo en un día válido para bloqueos o franjas.

## Campos de `clock`

| Campo | Tipo | Valor inicial o inferencia |
| --- | --- | --- |
| `start` | Hora `HH:MM`. | Inicio del primer intervalo explícito, o `07:40`. |
| `periods_per_day` | Número de intervalos que construir si faltan. | 6. |
| `period_minutes` | Duración positiva. | Duración del primer intervalo explícito, o 45. |
| `transition_minutes` | Minutos no negativos. | Menor separación entre intervalos explícitos, o 5. |
| `break_start` | Hora o `null`. | `10:05`. Se muestra como Merienda. |
| `break_end` | Hora o `null`. | `10:25`. |
| `lunch_start` | Hora o `null`. | `13:40`. |
| `lunch_end` | Hora o `null`. | `15:00`. |
| `lunch_after_period` | Entero no negativo. | 6. |

Una pausa se desactiva indicando `null` en ambos extremos. Los campos internos
`break_start` y `break_end` conservan su nombre por compatibilidad, aunque el texto
visible sea «Merienda».

`daily_periods`, cuando tiene contenido, determina los intervalos usados para
construir el ciclo. `clock` sigue describiendo los parámetros del editor. Los
archivos antiguos pueden tener intervalos que no correspondan con el reloj
actual; se mantienen al cargar.

## Franjas exactas

Una franja se representa así:

```json
{"week": 1, "day": 1, "period": 1, "start": "08:30:00", "end": "09:15:00"}
```

`week`, `day` y `period` son enteros. La combinación de los tres es única; `period`
comienza en 1. Las horas deben tener inicio anterior al final, y las franjas de
un mismo día no pueden solaparse ni invertir el orden temporal de sus turnos.
El lector utiliza `time.fromisoformat` para estas horas; el escritor emite su
representación ISO. La interfaz y las clases guardadas muestran horas a minutos.

Los guardados actuales de documentos y de configuraciones independientes incluyen
`slots`. Esta lista prevalece sobre la reconstrucción de intervalos y permite
conservar ciclos con horas diferentes entre semanas, jornadas sin franjas y el
orden exacto de almacenamiento. Si se omite, sigue funcionando el formato antiguo.

`planning_to_dict(planning)` omite esa lista por defecto para mantener una
representación compatible. Usa `include_slots=True` cuando necesites conservar
el modelo exacto. En ese modo también se conservan valores `null` de
`day_period_counts`, `teacher_unavailable_days` y `subject_unavailable_days`.
`null` representa metadatos no especificados en la API; no es una restricción
adicional.

## Horario generado y formato histórico

El bloque `generated` y los archivos antiguos `.horario.json` usan:

```json
{
  "type": "scholar-calendar-schedule",
  "version": 1,
  "planning": {},
  "slots": [],
  "lessons": []
}
```

Este es otro esquema de envoltura. `planning` contiene la configuración original;
`slots` contiene sus franjas exactas, y `lessons` las asignaciones. Una clase:

```json
{
  "week": 1,
  "day": 1,
  "period": 1,
  "classroom": "Grupo A",
  "subject": "Matemáticas",
  "teacher": "Ana",
  "start": "08:30",
  "end": "09:15"
}
```

La franja debe existir y las horas deben coincidir con ella. Aula, asignatura y
profesor deben existir. No puede repetirse un aula o un profesor dentro de la
misma franja. El archivo de horario requiere recursos no vacíos; un documento de
configuración sin horario sí puede representar un centro vacío.

Cargar valida consistencia estructural y ocupación, pero no vuelve a resolver ni
certifica que un horario modificado manualmente siga cumpliendo todas las
frecuencias o incompatibilidades del solver.

## Compatibilidad de carga

`load_project()` distingue tres casos:

1. `type = scholar-calendar-project`: restaura la configuración y el horario
   opcional por separado.
2. `type = scholar-calendar-schedule`: restaura el archivo anterior y usa su
   configuración como configuración editable y como configuración del horario.
3. Sin campo `type`: interpreta el archivo como una configuración independiente,
   sin horario generado.

Otros tipos o versiones se rechazan. Los formatos actuales no requieren renombrar
archivos antiguos. No existe migración automática al abrir; el nuevo formato se
escribe al guardar desde la aplicación. Una versión anterior del programa puede
ignorar el campo adicional `slots` de la configuración y no conservar ciclos
irregulares; utiliza la versión actual para esos documentos.

## Cambios cosméticos y preferencias

Los renombrados confirmados sin cambios de generación actualizan los nombres de
las clases y de la configuración del horario antes de guardar. No modifican sus
franjas. Los documentos pendientes de regenerar conservan ambas configuraciones;
la diferencia entre ellas permite recuperar el aviso al cargar.

Las preferencias de turnos 5.º–6.º y dobles sin merienda son criterios fijos del
motor actual. No añaden campos obligatorios ni cambian la versión de archivo.
Cargar un horario antiguo no lo reorganiza para cumplirlas.

## Validación y escritura

`validate_planning()` comprueba semanas, nombres, referencias, frecuencias,
días, sábados, reloj y franjas. No comprueba que todas las sesiones quepan ni que
haya docentes suficientes: esas condiciones corresponden a la generación.
`load_project()` transforma errores de estructura en `ValueError` y la interfaz
los muestra antes de sustituir su estado. Los errores de lectura/escritura del
sistema de archivos se comunican por separado como `OSError`.

`storage.write_json()`:

1. Escribe un temporal UTF-8 en el mismo directorio del destino.
2. Cierra el temporal y sustituye el destino mediante `os.replace`.
3. Retira el temporal en la limpieza final si aún existe.

La escritura usa indentación de dos espacios, caracteres Unicode y un salto de
línea final. Guardar no crea automáticamente directorios padre. Si falla antes
del reemplazo, se conserva el archivo anterior. No se generan copias de seguridad,
no se aplica cifrado y no hay una garantía adicional de persistencia física ante
un corte de alimentación mediante `fsync`.
