# Redondeo comercial del total final

Decisión del usuario, 30/09/2026: **redondear siempre el total final en ARS al peso
inferior**, a favor del cliente. Ejemplo: 1234.87 → 1234.0000. Cero y enteros no
cambian; un importe positivo menor a un peso pasa a cero.

Se aplica en backend al crear Quote, incluido el puente desde Quick Quote, y al
editar sus datos de precio: items, ajustes, markup o precio final. Primero se
resuelven todos los items y ajustes y se elige el precio explícito o sugerido;
después se aplica `Decimal` con `ROUND_FLOOR` al total. No redondear cada item.
Un precio manual también queda sujeto a esta regla. `final_price_overridden`
continúa indicando que el usuario proporcionó precio manual, no autoredondeo.

Los costos técnicos, cantidades, importes por item y precio sugerido conservan
su precisión. Preview y Quick Quote conservan su evaluación y precio sugerido;
el total final pertenece al Quote formal. Las monedas distintas de ARS conservan
su comportamiento, sin conversión implícita.

La seña se calcula sobre el total final ya redondeado, con su precisión existente.
Una seña fija que supera ese total se rechaza por la regla existente. Aprobar y
convertir copia los importes persistidos; no vuelve a aplicar el redondeo.

No hay migración ni backfill: lectura, aprobación y edición de textos de un
presupuesto anterior conservan su precio final. Una edición explícita de datos
de precio en draft aplica la política nueva. Los aprobados permanecen inmutables.

## Referencia normativa y alcance de la decisión

El [DNU 274/2019, artículo 74](https://www.argentina.gob.ar/normativa/nacional/decreto-274-2019-322236/texto)
contempla diferencias menores a un peso en el total a pagar cuando no puede
devolverse el vuelto exacto, a favor del consumidor. Su artículo 72 derogó la
Ley 22.802 y sus modificatorias. Fuente oficial consultada el 30/09/2026.

La decisión de redondear todos los totales finales ARS es una política comercial
más amplia elegida por el usuario. No atribuir a esa norma una obligación de
suprimir centavos en todo presupuesto. No introduce caja, cobros ni facturación
fiscal, y tampoco cambia el redondeo de los costos internos.
