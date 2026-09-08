"""Shared rule explanations for the help window and PDF export."""

RULE_SECTIONS = (
    (
        "Obligatorias",
        "Siempre se cumplen. Si no pueden cumplirse juntas, no se genera un horario.",
        (
            (
                "Frecuencia por semana y aula",
                "Cada asignatura se imparte en todas las aulas, exactamente tantas veces por semana como indique su frecuencia. Las sesiones no se compensan entre semanas.",
            ),
            (
                "Sin solapamientos",
                "Un aula solo puede tener una clase por turno. Un profesor solo puede impartir una clase por turno, aunque enseñe varias asignaturas o trabaje en varias aulas.",
            ),
            (
                "Profesores habilitados",
                "Solo se asignan profesores asociados a la asignatura y autorizados para el aula. Si una asignatura con sesiones previstas no tiene profesor elegible en un aula, la generación no puede continuar.",
            ),
            (
                "Repetición diaria",
                "Una asignatura normal aparece como máximo una vez al día en cada aula. Las asignaturas marcadas como dobles siguen las condiciones de la sección Dinámicas.",
            ),
            (
                "Solo en franjas disponibles",
                "Las clases se asignan a las semanas, días y turnos disponibles. Todos los grupos comparten las franjas del centro. Se permiten turnos vacíos; no es obligatorio llenar la jornada.",
            ),
            (
                "Configuración válida",
                "El ciclo admite de 1 a 52 semanas y días de lunes a sábado. Los nombres deben ser únicos dentro de cada tipo de recurso y las asociaciones deben referirse a recursos existentes. Las frecuencias no pueden ser negativas. Las franjas de un día deben estar ordenadas y no solaparse.",
            ),
            (
                "Alcance de la asignación",
                "La misma asignatura puede tener profesores distintos entre sesiones, incluso en una pareja doble. No se fijan profesores titulares ni se optimizan los huecos del profesorado, los cambios de aula o la carga diaria.",
            ),
        ),
    ),
    (
        "Dinámicas",
        "Dependen de los valores y restricciones que configures. Una vez aplicables, son obligatorias.",
        (
            (
                "Jornada y sábados",
                "La configuración determina las semanas del ciclo y los turnos de cada día. Los sábados solo tienen clases en las semanas activadas y si tienen turnos asignados. No hay clases los domingos.",
            ),
            (
                "Inicio, duración y pausas",
                "Las franjas se construyen desde la hora de inicio, con la duración de clase y el cambio configurados. Si una clase completa invadiría la merienda o la comida, se desplaza al final de esa pausa. No se recortan clases para encajarlas; puede quedar tiempo libre antes de una pausa.",
            ),
            (
                "Comida después de un turno",
                "El turno posterior al indicado para la comida comienza como mínimo a la hora de fin de la comida. Esta regla no añade turnos ni hace retroceder el reloj. El tiempo de cambio puede quedar incluido en una pausa.",
            ),
            (
                "Validez del reloj",
                "La duración debe ser positiva y el cambio no puede ser negativo. Cada pausa necesita inicio y fin, con el fin posterior al inicio; vaciar ambos la desactiva. Las pausas no pueden solaparse y las clases deben terminar antes de medianoche. Los archivos con franjas explícitas conservan sus horas: no se recalculan con el reloj mientras la jornada no cambie.",
            ),
            (
                "Asignaturas dobles",
                "Como máximo dos sesiones al día por aula. Cuando hay dos, deben ocupar turnos consecutivos del mismo día. Se admite como máximo una sesión suelta por semana y aula: una frecuencia de 4 forma dos parejas; una de 5 forma dos parejas y una sesión suelta. La consecutividad usa el número de turno, aunque exista una pausa entre ellos.",
            ),
            (
                "Aulas permitidas por profesor",
                "Si limitas las aulas de un profesor, solo puede trabajar en ellas. Sin una lista de aulas, puede impartir sus asignaturas en cualquiera.",
            ),
            (
                "Días bloqueados",
                "Una asignatura no se programa en sus días bloqueados. Un profesor tampoco puede impartir ninguna clase en los suyos. Ambos bloqueos se aplican a todas las semanas, durante todo el día.",
            ),
            (
                "Asignaturas no consecutivas",
                "Las dos asignaturas de cada pareja configurada no pueden ocupar turnos consecutivos en la misma aula, en ninguno de los dos órdenes. Se aplica incluso si hay una pausa entre turnos, pero no entre días distintos ni entre aulas distintas.",
            ),
            (
                "Asignaturas no simultáneas",
                "Las dos asignaturas de cada pareja configurada no pueden coincidir en el mismo turno del centro, considerando todas las aulas. Una sola de ellas sí puede impartirse en varias aulas a la vez con profesores distintos, siempre que la otra no aparezca en ese turno.",
            ),
        ),
    ),
    (
        "Opcionales",
        "El motor intenta cumplirlas. Puede dejarlas sin cumplir si hace falta para obtener un horario válido.",
        (
            (
                "Evitar quedar siempre en 5.º o 6.º",
                "Para cada asignatura, aula y semana, se intenta colocar al menos una sesión fuera de los turnos 5 y 6. Se cuenta un incumplimiento si todas sus sesiones quedan en esos dos turnos. También se aplica a asignaturas con una sola sesión semanal; no busca eliminar todas las clases de última hora.",
            ),
            (
                "Dobles sin merienda en medio",
                "Se intenta que la merienda no separe los dos turnos de una pareja doble. Se cuenta un incumplimiento por cada pareja que atraviesa el intervalo de merienda configurado. Sin merienda, esta preferencia no se aplica. La comida no tiene esta preferencia.",
            ),
            (
                "Misma importancia",
                "Las dos preferencias están siempre activas y tienen el mismo peso. El motor busca reducir la suma de sus incumplimientos respetando todas las reglas obligatorias y dinámicas.",
            ),
            (
                "Tiempo de búsqueda y resultados",
                "La búsqueda dispone de 10 segundos. Puede devolver un horario válido sin haber demostrado que es el mejor respecto a las preferencias. Si no encuentra ninguno a tiempo, lo indica sin afirmar que sea imposible. Si demuestra que las restricciones son incompatibles, avisa de que no existe un horario válido. Dos generaciones con los mismos datos pueden producir distribuciones distintas.",
            ),
        ),
    ),
)
