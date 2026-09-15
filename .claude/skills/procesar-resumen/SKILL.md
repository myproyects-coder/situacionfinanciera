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

Salida: `datos/movimientos.csv` con fecha, banco, tarjeta, titular, comercio, cuota,
pesos, usd, resumen y comprobante. El texto extraído queda en `datos/resumenes-texto/`.

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

Algunos no traen desglose y por eso no se pueden validar: la Mastercard de Galicia (no
separa por titular) y los meses sin consumos. El script los lista aparte. **No son un
error, pero tampoco están verificados** — decilo cuando uses esos datos.

## Después de procesar

1. Actualizá `Plan financiero.xlsx` si cambiaron saldos, mínimos o vencimientos.
2. Actualizá `ESTADO.md` con lo que haya cambiado.
3. Anotá qué falta: resúmenes que no están, meses incompletos, cargos sin identificar.
