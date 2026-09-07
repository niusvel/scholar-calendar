# Scholar Calendar

Aplicación de escritorio para organizar horarios escolares por semanas, aulas,
asignaturas y profesores. Genera una distribución que cumple las restricciones
configuradas, permite recuperarla desde un archivo y exporta un PDF con un día
por página.

El proyecto usa Python, Tkinter, OR-Tools y ReportLab. Funciona localmente, sin
servidor, cuentas ni base de datos. La interfaz está en español y se ha comprobado
en macOS.

## Empezar

Requiere Python 3.11 o posterior con Tkinter y una sesión gráfica.
Desde la carpeta del proyecto:

```sh
./run_app.sh
```

El script crea `.venv` e instala las dependencias cuando faltan. La instalación
inicial necesita acceso al repositorio de paquetes; el uso habitual es local.
También se puede instalar manualmente:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/scholar-calendar
```

La aplicación empieza con un centro vacío. Para probarla, elige **Archivo → Cargar**,
abre [examples/minimal.json](examples/minimal.json) y pulsa **Generar horario**.
El ejemplo contiene una semana, un grupo, dos profesores y cinco sesiones.

## Flujo habitual

1. Configura la jornada, los días lectivos, las asignaturas y los recursos.
2. Asocia los profesores a sus asignaturas y añade las restricciones necesarias.
3. Genera el horario y consulta su distribución por semanas.
4. Guarda el documento y exporta el PDF cuando lo necesites.

La jornada por defecto empieza a las **08:30**, con clases de **45 minutos** y
cambios de **5 minutos**. La **merienda** es de **10:05 a 10:25** y la **comida**,
de **13:40 a 15:00**. El ciclo inicial tiene una semana, seis turnos diarios de
lunes a viernes y ningún sábado activo.

**Guardar** conserva la configuración actual y el horario generado, si lo hay,
en un único JSON. Si editas después de generar, conserva también la configuración
con la que se calculó ese horario. **Cargar** lo recupera sin recalcular.
**Limpiar** vacía la ventana y restablece los valores iniciales; no elimina archivos.

## Documentación, de lo general a lo detallado

| Lectura | Contenido |
| --- | --- |
| [Guía de uso](docs/01-guia-de-uso.md) | Instalación, pantallas, formularios, guardado, PDF y resolución de problemas. |
| [Arquitectura](docs/02-arquitectura.md) | Módulos, dependencias, estados de la interfaz y flujo de datos. |
| [Reglas del planificador](docs/03-planificacion.md) | Reloj, frecuencias, dobles turnos, incompatibilidades y modelo de restricciones. |
| [Formatos de archivo](docs/04-formatos.md) | Campos JSON, versiones, compatibilidad, validación y escritura atómica. |
| [Desarrollo y API](docs/05-desarrollo.md) | Referencia de funciones y modelos, ejemplos Python, estilos, pruebas y mantenimiento. |
| [Revisión del proyecto](docs/06-revision.md) | Correcciones de la revisión, validaciones realizadas y límites actuales. |

El archivo [examples/cycle.json](examples/cycle.json) conserva un ejemplo más
amplio con intervalos explícitos y campos históricos. Sus horas son propias del
ejemplo; no representan los valores iniciales actuales.

## Comprobar el proyecto

Con las dependencias de desarrollo instaladas:

```sh
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/python -m pytest
```

Las pruebas de interfaz se omiten normalmente. En una sesión de escritorio:

```sh
SCHOLAR_CALENDAR_GUI_TESTS=1 .venv/bin/python -m pytest
```

No hay guardado automático ni histórico automático. La generación busca una
solución válida, no una distribución pedagógica óptima ni reproducible entre
ejecuciones. Estos límites se explican en la documentación técnica.
