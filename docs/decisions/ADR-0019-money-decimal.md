# ADR-0019: Importes con Decimal y NUMERIC

- Estado: aceptada
- Fecha: 2026-08-14

## Contexto

Los valores binarios de punto flotante no representan importes decimales de
forma exacta y pueden introducir diferencias en costos futuros.

## Decisión

Usar `Decimal` en Python y `NUMERIC(18, 4)` en PostgreSQL para dinero. Conservar
el código de moneda junto a cada importe histórico.

## Consecuencias

- `float` queda prohibido para precios y costos.
- La configuración de moneda no reinterpreta importes ya persistidos.
- No se crea todavía una entidad `Money` ni conversión monetaria.
