# ADR-0011: Frontend con Nuxt 4

- Estado: aceptada
- Fecha: 2026-07-28

## Contexto

El frontend necesitaba una base tecnológica sin anticipar el diseño visual.

## Decisión

Se utilizarán Nuxt 4, Vue 3 y TypeScript estricto en modo SPA, inicialmente sin
SSR. Nuxt UI y Tailwind cubrirán componentes y estilos; TanStack Query,
Pinia y Zod tendrán responsabilidades separadas. El cliente se generará desde
OpenAPI cuando sea posible.

## Consecuencias

- pnpm administrará dependencias.
- Vitest y Playwright cubrirán pruebas.
- Las convenciones exactas de Nuxt 4 se verificarán antes de crear la
  estructura.
- Este ADR no define pantallas ni navegación.
