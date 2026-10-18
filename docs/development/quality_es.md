# Calidad e integración continua

## Cierre automatizado local

```bash
./scripts/check-local.sh
# Equivalentes:
make check-local
make ci
```

Requiere Docker Engine, Compose >= 2.20 y Bash. No necesita servicios de desarrollo
encendidos ni Python/Node en el host. Construye imágenes desde el checkout y crea
un proyecto único por ejecución, sin puertos publicados ni bind mounts.

- Dos PostgreSQL efímeros separados: integración (`rrii_coach_test`) y navegador
  (`rrii_coach_e2e`). No se usan volúmenes persistentes ni datos de prueba humana.
- Alembic: instalación vacía, downgrade a base, upgrade, current y check.
- Backend: Ruff, formato, mypy y pytest completo, sin filtrar integración.
  El OpenAPI versionado debe coincidir con el esquema real de FastAPI.
- Frontend: Vitest, lint/typecheck y build. El script `lint` actual es alias del
  typecheck de Nuxt; no se presenta como una ejecución de ESLint.
- Playwright contra el frontend compilado, API y PostgreSQL reales. Chromium
  general y navegación táctil son proyectos explícitos. Algunas pruebas
  interceptan respuestas para validar errores o contratos visuales; no se presenta
  toda la cobertura como integración sin mocks.
- Los informes deben contener casos y no pueden tener omisiones, fallos o casos
  inestables. Se prohíbe `test.only`, se usa un worker y no hay reintentos.

Al terminar, incluso ante fallo, se copian informes a `reports/checks/<ejecución>/`
y se retiran los contenedores y la red de ese proyecto. Las bases y archivos
sintéticos desaparecen con los contenedores; las imágenes/caché quedan en disco.
Los informes están ignorados por Git. Un fallo de Docker durante la limpieza se
informa y devuelve error; no se detienen proyectos ajenos.

La CI conserva sus verificaciones por componente y agrega el mismo ejecutor
completo, con informes como artefactos de diagnóstico. La configuración del workflow
no equivale a una ejecución ya realizada en GitHub. No publicar ni hacer push
sin autorización.

## Playwright y configuración explícita

No hay IPs Docker fijas ni omisiones por ausencia de API. Una ejecución directa
exige `RRII_E2E_API_BASE` terminado en `/api/v1`, con PostgreSQL y archivos aislados.
Si se define `NUXT_PUBLIC_API_BASE_URL`, debe coincidir. El frontend de prueba abre
el puerto 3100 dentro del contenedor y la API admite ese origen mediante CORS.

La colección actual incluye 76 casos en 23 archivos, cuatro de ellos exclusivos
del proyecto `chromium-touch`. El proyecto `chromium` incluye los demás casos,
con tamaños de pantalla explícitos en cada prueba. La colección no certifica
aprobación; los resultados efectivos se registran en cada checkpoint.

No se reutiliza un servidor frontend ya iniciado: evita probar accidentalmente
otro checkout. El runner instala Chromium y sus bibliotecas en la imagen de
testing, con ejecución como usuario sin privilegios.

## Comprobación rápida de desarrollo

Con los servicios de desarrollo iniciados, `make check` ejecuta las validaciones
habituales por componente, sin reemplazar el cierre aislado anterior.
La prueba humana utiliza [su entorno propio](human_test_environment_es.md) y se
realiza separadamente de las suites que modifican datos.

## Pre-commit dentro de un contenedor

La opción recomendada no instala Python ni Node en el host:

```bash
make precommit
make precommit-all
```

El primer uso construye una imagen auxiliar versionada por su Dockerfile. Los
hooks verifican archivos comunes, claves privadas, archivos grandes, Ruff,
formato Python y sintaxis Bash. `make precommit-all` incluye además los archivos
nuevos todavía no agregados al índice de Git.

## Hooks integrados con Git

Para ejecutar automáticamente los hooks al hacer commit, instalar pre-commit
de forma aislada en el host:

```bash
sudo apt install pipx
pipx ensurepath
pipx install pre-commit==4.6.0
make precommit-install
```

Abrir una sesión nueva si `pipx ensurepath` modificó el entorno. Esta
instalación es opcional y no convierte Python, uv o Node en requisitos del
proyecto. No se debe instalar pre-commit dentro del Python del sistema.

## Dependencias

Los lockfiles son obligatorios. Python se instala con `uv sync --frozen` y el
frontend con `pnpm install --frozen-lockfile`. Dependabot revisa semanalmente
GitHub Actions, Python, pnpm y las imágenes Docker, sin auto-merge.

No se agrega un badge de CI hasta que exista un remoto definitivo.
