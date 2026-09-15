---
name: procesar-resumen
description: Procesa resúmenes de tarjeta de crédito nuevos (Galicia, Santander, BBVA) y actualiza el CSV de movimientos. Usalo cuando aparezcan PDFs de resúmenes nuevos en frances/, galicia/ o santander/, o cuando Agustina diga que cerró una tarjeta y pase los archivos. También cuando haya que reprocesar todo después de tocar el parser.
---

# Procesar resúmenes

## Regla que no se negocia

**Ningún número se afirma sin reconciliar contra el total que declara el propio PDF.**

El script lo hace solo y **se niega a escribir el CSV si algo no cierra**. Si falla, no
lo fuerces ni subas la tolerancia: andá a ver qué línea falta. Las tres veces que pasó,
el parser estaba mal, no el PDF.

## Cómo se corre

```bash
python3 scripts/procesar_resumenes.py
```

Procesa todo lo que haya en `frances/`, `galicia/` y `santander/`. Para archivos sueltos:

```bash
python3 scripts/procesar_resumenes.py ruta/al/resumen.pdf
```

Salida:
- `datos/movimientos.csv`: fecha, banco, tarjeta, titular, comercio, cuota, pesos, usd,
  resumen y comprobante.
- `datos/resumenes.csv`: un renglón por resumen con cierre, vencimiento, próximo cierre y
  vencimiento, total ARS/USD, mínimo, pagos, intereses, punitorios, comisiones,
  percepciones (neto débito − devolución) y consumos. **Es la tabla para seguir la deuda
  mes a mes: ESTADO.md sale de acá, no se copia a mano.**

El texto extraído de los PDF queda en `datos/resumenes-texto/`.

Santander entrega desde septiembre 2026 "Último resumen" en **xlsx**: va en `santander/`
renombrado como `Resumen de tarjeta de crédito VISA|AMEX-DD-MM-AAAA.xlsx` con la fecha de
**vencimiento** (mismo criterio que los PDF). Si el mismo resumen está en PDF y xlsx, manda
el PDF. Los comprobantes de pago no van sueltos en las carpetas de bancos: van en
`<banco>/comprobantes/`.

## Qué hacer con la salida

**No leas los .txt crudos.** Son ~19.000 caracteres por resumen y no hace falta ninguno
para analizar: trabajá sobre el CSV con pandas o con un script. Leer los PDF enteros al
contexto fue el mayor desperdicio de la sesión de agosto 2026.

Si necesitás el detalle de un resumen puntual, `grep` sobre el .txt correspondiente. No
lo abras entero.

## Cuando falla la reconciliación

El mensaje dice qué resumen, qué titular, cuánto dice el PDF y cuánto salió parseado.
Diferencias que ya aparecieron y su causa:

| Síntoma | Causa real |
|---|---|
| Parseado **mayor** que el PDF | faltan los reintegros (importes negativos) |
| Diferencia igual a la suma de consumos en el exterior | se están tomando importes en BRL o EUR como si fueran pesos |
| Titulares cruzados en Galicia | el marcador `Total Consumos de X` **cierra** el bloque anterior, no abre el siguiente |

Ese último es el que más caro sale: invierte quién gastó qué y el análisis entero sale
al revés sin que nada parezca roto.

## Resúmenes sin totales declarados

Algunos no traen desglose y por eso no se pueden validar: los meses sin consumos. La
Mastercard de Galicia sí se valida contra `TOTAL CONSUMOS DEL MES` (no separa por titular:
todo es de Agustina; sus consumos en el exterior traen el importe en la columna dólares). El script los lista aparte. **No son un
error, pero tampoco están verificados** — decilo cuando uses esos datos.

## Después de procesar

1. Leé `datos/resumenes.csv` para saldos, mínimos, vencimientos, intereses y punitorios.
2. Actualizá `ESTADO.md` con esos números y `Plan financiero.xlsx` si cambiaron.
3. Commiteá: la carpeta tiene git desde septiembre 2026.
4. Anotá qué falta: resúmenes que no están, meses incompletos, cargos sin identificar.
