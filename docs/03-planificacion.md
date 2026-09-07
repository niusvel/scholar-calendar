# Reglas y motor de planificación

[← Arquitectura](02-arquitectura.md) · [Inicio](../README.md) · [Formatos →](04-formatos.md)

## Unidades del modelo

- **Ciclo:** entre 1 y 52 semanas numeradas desde 1.
- **Día:** 1 es lunes y 6 es sábado. No hay domingo lectivo.
- **Turno:** posición ordinal de una clase dentro de un día.
- **Franja (`PlanningSlot`):** semana, día, turno, inicio y final disponibles.
- **Sesión (`ScheduledLesson`):** asignatura y profesor asignados a una franja de un aula.

Los días y semanas son relativos. No hay fechas reales ni zona horaria en los
archivos; las horas representan el reloj local del centro.

## El reloj escolar

`build_daily_periods()` comienza en la hora indicada y construye clases completas.
Después de cada clase avanza la duración del cambio. Antes de ubicar una clase,
comprueba las pausas: si esa clase invadiría una de ellas, desplaza el inicio al
final de la pausa. Las pausas se consideran intervalos `[inicio, fin)`: terminar
justo cuando empieza una pausa, o empezar justo cuando acaba, es válido.

Con los valores iniciales:

| Actividad | Intervalo |
| --- | --- |
| Turno 1 | 08:30–09:15 |
| Cambio | 09:15–09:20 |
| Turno 2 | 09:20–10:05 |
| Merienda | 10:05–10:25 |
| Turno 3 | 10:25–11:10 |
| Cambio | 11:10–11:15 |
| Turno 4 | 11:15–12:00 |
| Cambio | 12:00–12:05 |
| Turno 5 | 12:05–12:50 |
| Cambio | 12:50–12:55 |
| Turno 6 | 12:55–13:40 |
| Comida, si continúa la jornada | 13:40–15:00 |
| Turno 7, si se configura | 15:00–15:45 |

El cambio puede quedar absorbido por una pausa. Por ejemplo, no se añaden otros
cinco minutos después de la merienda que sigue al turno 2. La comida tiene
además `lunch_after_period`: el turno siguiente al indicado no puede empezar antes
de `lunch_end`. El cálculo usa el máximo con la hora actual, por lo que no hace
retroceder el reloj si las clases ya van más tarde.

No cabe una clase parcial antes de una pausa. Si sobran minutos después del
cambio, `daily_rows()` los identifica como tiempo libre. Esta función descompone
los huecos entre franjas usando sus límites, las pausas y el tiempo de cambio.
Fusiona segmentos contiguos de una misma pausa y no añade actividades después de
la última franja.

Se rechazan duración no positiva, cambios negativos, turnos negativos, una pausa
con un solo extremo, un final anterior o igual al inicio, pausas solapadas y
clases que terminan a medianoche o después. Las franjas explícitas de un archivo
son una entrada distinta: se valida su orden y ausencia de solapamientos, pero no
se fuerzan a coincidir con el reloj generador ni se recortan por sus pausas.

## Frecuencias y recursos

Cada asignatura se programa en todas las aulas. Su frecuencia se exige en cada
semana y aula, aunque una semana tenga más días lectivos que otra. No se compensa
una semana incompleta con sesiones adicionales en otra.

La API conserva el nombre histórico `Subject.lessons_per_cycle`; su significado
es **sesiones por semana y aula**. El JSON actual utiliza `lessons_per_week`.
Una frecuencia de cero es válida para el modelo y los archivos, aunque el
formulario de altas y cambios exige al menos una sesión.

Un profesor es elegible si la asignatura pertenece a `teacher_subjects[profesor]`
y el aula está permitida. Un conjunto vacío o ausente en `teacher_classrooms`
significa que no tiene limitación de aulas. Si una asignatura con frecuencia
positiva no tiene ningún profesor elegible en un aula, se informa antes de
resolver.

En una franja no pueden coincidir dos clases del mismo profesor ni dos clases
en la misma aula. Las celdas libres están permitidas: no se exige llenar todos
los turnos. El modelo no obliga a mantener un único profesor para una asignatura,
para un aula o para una pareja de turnos dobles.

## Repetición diaria y turnos dobles

Una asignatura normal puede aparecer como máximo una vez por día en un aula.
Por tanto, una frecuencia semanal superior al número de días disponibles no
puede cumplirse para esa asignatura.

Una asignatura marcada como doble:

1. Puede aparecer como máximo dos veces al día en cada aula.
2. Las dos sesiones del mismo día deben ocupar turnos consecutivos.
3. Puede tener como máximo una sesión suelta por semana y aula.

Así, una frecuencia de 4 produce dos parejas; una de 5 produce dos parejas y una
sesión suelta. La consecutividad se basa en el número de turno dentro de la misma
semana y día, **no** en que el final de una clase coincida con el inicio de la
siguiente. Una pareja puede quedar a ambos lados de la merienda o la comida.

## Bloqueos e incompatibilidades

Los días bloqueados de un profesor o asignatura se aplican en todas las semanas.
No se configuran intervalos de indisponibilidad dentro de un día, ni excepciones
para una semana concreta.

`forbidden_consecutive` contiene parejas de asignaturas que no pueden ocupar
turnos ordinales adyacentes en una misma aula, en ninguno de los dos órdenes.
No afecta a aulas diferentes ni al último turno de un día frente al primero del
siguiente.

`forbidden_parallel` impide que las dos asignaturas de una pareja estén presentes
en el mismo turno, considerando todas las aulas. No limita cuántas aulas pueden
impartir simultáneamente una sola de ellas. Por ejemplo, si A y B son incompatibles,
A puede ocupar Aula 1 y Aula 2 a la vez con profesores distintos, siempre que B
no aparezca en ese turno.

## Formulación CP-SAT

`solve()` valida primero la estructura de `PlanningInput`. A continuación crea:

- Una variable binaria `lesson[aula, asignatura, profesor, índice_de_franja]` por
  combinación elegible y no bloqueada.
- Una variable `presence[aula, asignatura, índice_de_franja]` igual a la suma de
  sus asignaciones posibles de profesor.
- Variables de parejas y sesiones sueltas para asignaturas dobles.
- Una variable de elección por pareja incompatible y franja: si se activa, anula
  todas las sesiones de la segunda asignatura; si no, anula las de la primera.

Se indexan las variables por aula/franja, profesor/franja, asignatura/franja y
semana para construir las restricciones sin recorrer todos los candidatos cada
vez. Las franjas de cada día se ordenan por turno antes de buscar adyacencias,
por lo que el orden de almacenamiento no cambia las reglas de dobles turnos.

Todas las reglas descritas son obligatorias. No existe función objetivo:
las restricciones de dobles ya fijan el número de parejas necesario y no requieren
una maximización adicional.

El solver dispone de **10 segundos** y **8 workers**. Se aceptan los estados
`OPTIMAL` y `FEASIBLE`. `UNKNOWN` produce un mensaje de tiempo agotado sin afirmar
que el problema sea imposible. Los demás estados no aceptados producen un error
de planificación. El resultado se ordena por semana, día, turno y aula.

## Qué no optimiza ni modela

No se minimizan huecos de profesores, cambios de aula, primeras o últimas horas,
carga diaria ni preferencias pedagógicas. No hay materias específicas por aula,
profesores titulares fijos, capacidad física del aula, horarios independientes
por grupo ni bloqueo manual de una celda del resultado.

Todos los grupos comparten las franjas del centro. La disponibilidad de un
profesor se controla por índice de franja; la validación exige que las franjas
de un día estén ordenadas y no se solapen. No hay garantía de producir la misma
solución en dos ejecuciones, aunque la configuración no cambie.
