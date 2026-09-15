# bita / dose — registro de gastos

Cargar cada gasto acá **cuando ocurre**, no al final. Lo que no está en esta tabla no
existe para el plan financiero, y termina apareciendo como "gasto personal" en el análisis
de tarjetas.

**Por qué importa separarlo:** desde un resumen de tarjeta no se distingue un pago a
proveedor de un gasto personal — sólo se ve `MERPAGO*NOMBRE`. En el análisis de enero a
junio 2026 esto llevó a atribuirle al proyecto US$ 641/mes cuando en realidad eran
US$ 910/mes, y a contar como gasto propio transferencias que eran del negocio.

## Cómo cargar

Una fila por comprobante. Si no hay comprobante, ponerlo igual y marcarlo.

| fecha | concepto | categoría | ARS | quién pagó | comprobante | ¿tarjeta? |
|---|---|---|---|---|---|---|
| 2026-04-01 | Pago 1 Ana | desarrollo-fooding | 846.000 | Flor | 152115180897 | no |
| 2026-04-15 | Registro de marcas ⚠ **rechazado** | registro-inpi | 820.000 | Agustina | 154109974525 | Santander VISA |
| 2026-05-01 | Primer pago Ana | desarrollo-fooding | 990.500 | Flor | 157279993122 | no |
| 2026-05-18 | Pago Ana | desarrollo-fooding | 994.000 | Flor | 159106663305 | no |
| 2026-05-18 | Pago Ana | desarrollo-fooding | 1.988.000 | Agustina | 159919739072 | no |
| 2026-06-23 | Arancel INPI marca | registro-inpi | 50.413 | Agustina | 164703476781 | no |
| 2026-06-24 | Arancel INPI marca | registro-inpi | 38.192 | Agustina | 165670383384 | no |
| 2026-06-26 | Arancel INPI marca | registro-inpi | 38.192 | Agustina | 165948346194 | no |
| 2026-06-26 | Registro INPI categoría 30 | registro-inpi | 125.270 | Flor | 165951831398 | no |
| 2026-07-08 | Fábrica — Ana | desarrollo-fooding | 604.000 | Flor | 166995786227 | no |
| 2026-07-09 | Pago 1 Carly | diseño | 705.170 | Agustina | 168047720914 | no |
| 2026-07-22 | Packaging Ana | desarrollo-fooding | 900.000 | Flor | 169996227928 | no |
| 2026-07-22 | Queso crema | insumos-prueba | 75.000 | Flor | sin comprobante | no |

**Total al 28/07/2026: $8.174.737** — Flor $4.534.770 (55%), Agustina $3.639.967 (45%).
Para emparejar 50/50, Agustina debe $447.401.

## Comprometido, todavía no pagado

| fecha | concepto | ARS | quién |
|---|---|---|---|
| 2026-08-09 | Pago 2 Carly | 708.000 | Agustina |
| 2026-09-09 | Pago 3 Carly | 708.000 | Agustina |

Si Agustina paga los dos, queda en **53%** del aporte total ($5.055.967 de $9.590.737),
o sea $260.598 por encima de Flor. Hoy debe $447.401 para emparejar: los dos pagos de
Carly corrigen de más.

## Lo que falta estimar

La etapa de desarrollo costó ~$2.043.684/mes entre las dos. **La de producción no está
estimada y es otra cosa.** El único insumo que figura son $75.000 de queso crema de prueba.

Para poder proyectar hace falta:

- Costo hasta la primera tanda (insumos en volumen, envases, fabricación)
- Capital de trabajo para sostener producción una vez que arranque
- Precio por unidad y volumen estimado
- Si hay más pagos comprometidos además de Carly

## Cómo se financia

Lo que pone Agustina sale de su flujo o de préstamos de Maxi y sus papás. **Dejar
asentado cuál de las dos cosas es cada peso**: aporte de capital al proyecto (cambia el
porcentaje societario) o préstamo personal a devolver (es pasivo suyo). Hoy no está
distinguido y es la diferencia entre tener el 45% o el 53% del negocio.
