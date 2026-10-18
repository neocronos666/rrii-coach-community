# Convenciones de commits

El proyecto adopta Conventional Commits:

```text
tipo(ámbito opcional): descripción
```

Tipos admitidos inicialmente:

- `feat`: nueva capacidad funcional;
- `fix`: corrección;
- `docs`: documentación;
- `refactor`: cambio interno sin alterar comportamiento;
- `test`: pruebas;
- `chore`: mantenimiento;
- `ci`: integración continua;
- `build`: sistema de construcción o dependencias;
- `perf`: rendimiento;
- `revert`: reversión explícita.

Ejemplos:

```text
chore: preparar entorno reproducible
fix(frontend): agregar tipos de Node
ci: agregar validaciones automáticas
docs: documentar flujo local
```

La descripción se escribe en castellano, en imperativo y sin punto final. Cada
commit debe representar una unidad coherente y dejar el repositorio validable.
No se exige Commitlint ni Husky en esta etapa.
