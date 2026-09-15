# Situación financiera — Agustina

Espacio de trabajo para analizar y ordenar la situación financiera personal: tarjetas,
deuda, proyecto propio (postres congelados) y decisiones de ahorro/inversión.

## Estructura

```
.
├── ESTADO.md                     Foto verificada. Se lee primero y se actualiza al cerrar.
├── PLAN-CARRERA.md               Fases, cadencia y puntos de decisión hasta 2034
├── Plan financiero.xlsx          Tarjetas, plan de pago, reembolsos, plan 12 meses y a 2034
├── frances/ galicia/ santander/  Resúmenes en PDF, tal como los descarga el banco
│                                 (Santander desde sep-2026 también en .xlsx: el parser todavía no los lee)
├── ingresos/recibos-ort/         Recibos de sueldo de ORT (2025)
├── carrera/                      Puesto de Roxom (Senior Accounting Specialist)
│   ├── cv/                       CV en PDF y su fuente LaTeX (main.tex, RenderCV)
│   └── actuaria-tasp/            Guía de TP y práctica de la última materia
├── scripts/procesar_resumenes.py Extractor con reconciliación obligatoria
├── scripts/modelo_inmuebles.py   Genera contexto/inmuebles/escenarios-deptos.xlsx
├── datos/movimientos.csv         Movimientos parseados y validados  <- trabajar acá
├── datos/resumenes-texto/        Texto crudo (generado; NO leer entero)
├── contexto/
│   ├── conversaciones-chatgpt/   Resúmenes de conversaciones previas con ChatGPT (2025)
│   ├── inversiones/              Marco de cartera y relevamientos del agente `mercados`
│   ├── inmuebles/                Escenarios de deptos con Maxi, modelo y relevamiento de portales
│   └── proyecto/                 Números del proyecto de postres congelados
├── .claude/agents/mercados.md    Agente de información de mercados
├── .claude/skills/procesar-resumen/
├── .claude/skills/relevar-inmuebles/
└── CLAUDE.md
```

## Lógica de resolución

Cuatro reglas. Salieron de errores concretos de la sesión de agosto 2026, no de teoría.

**1. Reconciliar antes de afirmar.** Ningún número se enuncia sin cruzarlo contra el total
que declara la fuente. `scripts/procesar_resumenes.py` lo hace y se niega a escribir si no
cierra. En esa sesión hubo seis correcciones; cuatro las habría evitado este paso solo. La
peor fue una atribución cruzada entre titulares que invertía quién gastó qué sin que nada
pareciera roto.

**2. Extraer a disco antes de leer.** Los PDF no entran crudos al contexto: se parsean, se
validan y se consulta el CSV. Cada resumen son ~19.000 caracteres para sacar cinco números.
Si hace falta el detalle de uno puntual, `grep` sobre su `.txt`, no abrirlo entero.

**3. Delegar el trabajo sucio.** La extracción masiva va en subagente, cuyo contexto se
descarta. Vuelve el CSV validado, no el texto.

**4. `ESTADO.md` se lee al empezar y se actualiza al terminar.** Es lo que evita reconstruir
en cada sesión qué era cada transferencia grande.

## Cómo trabajar acá

**Los PDF son la fuente de verdad.** Cualquier número que se afirme tiene que poder
rastrearse hasta un resumen concreto. Si un dato viene de otro lado (una conversación,
una estimación, algo que dijo Agustina), decirlo explícitamente.

**Resúmenes nuevos:** usar el skill `procesar-resumen`, que corre
`scripts/procesar_resumenes.py`. No parsear a mano.

No hay `pdftotext` ni LibreOffice instalados. Para Excel se usa `openpyxl`; como no hay
motor de recálculo, los libros se guardan con `wb.calculation.fullCalcOnLoad = True`.

**Dónde está cada dato en cada resumen:**

| Banco | Saldo total | Pago mínimo | Detalle |
|---|---|---|---|
| Galicia | línea `TOTAL A PAGAR` | bloque `PAGO MINIMO` de la página 1 | Consumos separados por titular y adicional |
| Santander | última línea del PDF, después de `TNA … TEM …` | línea siguiente, sola | `Su saldo financiado:` en la anteúltima página |
| BBVA | `SALDO ACTUAL $` | `PAGO MÍNIMO $` | Etiqueta y valor van en renglones separados |

**Nombres de archivo poco confiables:** los PDF de BBVA se llaman todos `Resumen (n).pdf`
sin relación con la fecha. Siempre verificar `CIERRE ACTUAL` adentro del archivo.

## Ingresos (desde agosto 2026)

- ORT: $426.000 ARS (~US$ 300, en pesos: se licúa entre paritarias)
- **Roxom: 1.600 USDT** (84% del total, dolarizado)
- **Total ≈ US$ 1.900/mes**

Aumento de agosto: Roxom de US$ 1.000 a 1.600. El objetivo que ella fijó en 2025 es
US$ 3.500/mes; el pico histórico fue US$ 1.964 en abril 2025.

## Proyecto propio: postres congelados

No confundir con OrbitPay, que es un proyecto distinto y anterior (el resumen sigue en
`contexto/conversaciones-chatgpt/` como referencia). Buena parte de las transferencias
por Mercado Pago que aparecen en los resúmenes corresponden a los postres, pero **desde
el resumen no se puede distinguir un pago a proveedor de un gasto personal**: la tarjeta
sólo muestra `MERPAGO*NOMBRE`. Hay que preguntarle a Agustina.

## Estado y objetivos

**Objetivo de fondo:** calificar para un crédito hipotecario. Todo lo demás (nivel de
consumo, uso de tarjetas, mora) se evalúa contra eso.

**Reglas que Agustina ya fijó en 2025 y siguen vigentes:**

- Las tarjetas se pagan **siempre por el total**. Nunca pago mínimo, nunca refinanciación
  del resumen.
- Si hace falta deuda, se toma por fuera de la tarjeta y se compara siempre por CFTEA,
  no por TNA.
- No dejar saldos grandes en pesos: convertir *just in time*, 24–48 h antes de cada
  vencimiento.
- Nada de apalancamiento ni de operar para "recuperar" una pérdida.
- No tomar deuda para invertir mientras el costo del crédito (~7% mensual) supere el
  rendimiento razonable de mercado (~2% mensual). Ese carry es negativo y ya está
  demostrado con números en `contexto/conversaciones-chatgpt/resumen_conversacion_finanzas.txt`.
- **Ninguna tarjeta pasa el vencimiento sin el mínimo COMPLETO.** El mínimo a medias no
  sirve: en mayo 2026 pagó $40.120 de $79.730 y entró en mora igual.
- **Los consumos en moneda extranjera se pagan CON moneda extranjera**, antes de las 19h
  del vencimiento. Evita la percepción del 30% sin trámite. Probado: en agosto 2026 le
  reintegraron $562.677,96 por haber pagado U$S 1.310 en dólares.

**Tono pedido explícitamente:** directo y honesto, sin validación innecesaria.
Cuestionar supuestos y autoengaños. Priorizar planes concretos.

## Límite importante

En este espacio se hacen **cuentas**, no recomendaciones de inversión. Está bien calcular
rendimientos, costos, break-evens, comparar CFTEA contra retorno esperado y llevar el
registro de la cartera. No corresponde decidir qué comprar o vender, ni opinar sobre si
una cartera es adecuada para su perfil: eso lo define ella, con un asesor matriculado si
hace falta.

## Al cerrar un análisis

- Actualizar `Plan financiero.xlsx` si cambiaron saldos o vencimientos.
- Dejar anotado qué información falta (resúmenes que no están, números que no se tienen).
- No inventar el dato faltante ni estimarlo en silencio.
