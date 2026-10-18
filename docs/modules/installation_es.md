# Configuración de la instalación Community

## Finalidad

Community posee una única configuración funcional activa, sin usuarios ni
organizaciones visibles. La API expone un contrato tipado y el almacenamiento
interno reutiliza `SystemSetting` bajo la clave técnica
`community.installation_settings`.

El resto del dominio no debe consultar claves arbitrarias. Debe utilizar
`InstallationSettingsService`, que valida y traduce el documento persistido.

## Campos y valores iniciales

| Campo | Valor inicial | Regla |
|---|---|---|
| `business_name` | `null` | Nombre opcional del negocio. |
| `currency` | `ARS` | Formato ISO 4217 de tres letras mayúsculas. |
| `country_code` | `AR` | Formato ISO 3166-1 alpha-2. |
| `region` | `null` | Texto regional flexible. |
| `timezone` | `America/Argentina/Buenos_Aires` | Identificador IANA. |
| `language` | `es` | Código de idioma inicial. |
| `deposit_policy` | `none` | `none`, `optional` o `required`. |
| `deposit_type` | `null` | `fixed` o `percentage` cuando aplica. |
| `deposit_value` | `null` | Decimal no negativo. |

Los defaults se devuelven aunque todavía no exista un registro. La primera
actualización persiste el documento completo de forma transaccional.

## Tarifas técnicas

La configuración incorpora precio eléctrico por kWh y tarifas horarias de
diseño, preproducción, posproducción, ensamblaje, soporte, capacitación y
pretransporte. Todas son `Decimal`, usan la moneda principal y su default es
`null`. `null` significa no configurada; cero es una decisión explícita de no
imputar costo.

`default_markup_percentage` también es opcional. Su ausencia equivale a markup
cero al crear un presupuesto, decisión que queda explícita y congelada en él.

## Seña

Una política `none` no admite tipo ni valor. Las políticas `optional` y
`required` exigen ambos. Un valor fijo es no negativo y un porcentaje se
encuentra entre 0 y 100. Este módulo no registra pagos ni facturación.

## API

- `GET /api/v1/settings`: obtiene configuración o defaults.
- `PUT /api/v1/settings`: reemplaza la configuración completa validada.

No existen POST, DELETE, autenticación ni configuraciones múltiples.
