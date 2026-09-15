---
name: relevar-inmuebles
description: Releva publicaciones de Zonaprop/Argenprop para Caballito con el navegador integrado y las vuelca a datos/inmuebles/AAAA-MM-DD.csv. Usalo cuando Agustina pida actualizar precios de venta o alquiler, o una vez por mes para mantener la serie.
---

# Relevar inmuebles

Objetivo: una fila por publicación en `datos/inmuebles/AAAA-MM-DD.csv`, con columnas
`fecha,portal,operacion,ambientes,m2,precio,moneda,expensas,direccion,zona,url`.

## Procedimiento

1. Abrir con el navegador integrado (`mcp__Claude_Browser__navigate`) cada búsqueda:
   - `https://www.zonaprop.com.ar/departamentos-alquiler-caballito-2-ambientes.html`
   - `https://www.zonaprop.com.ar/departamentos-venta-caballito-2-ambientes.html`
   - `https://www.zonaprop.com.ar/departamentos-venta-caballito-3-ambientes.html`
   - `https://www.zonaprop.com.ar/departamentos-venta-caballito-4-ambientes.html`
   Si una da bloqueo o captcha, **no resolverlo**: anotar que falló y seguir con la siguiente.
2. Leer el texto con `get_page_text` (máx. 20.000 caracteres) y extraer las tarjetas. Cada
   tarjeta empieza con el precio (`USD 189.000` o `$ 900.000`), sigue con expensas
   opcionales, `NN m² tot.`, `N amb.`, dirección y zona. Ignorar la descripción larga.
3. Paginar con `-pagina-2.html` hasta tener al menos 40 avisos por búsqueda, o hasta la
   página 3, lo que llegue primero.
4. Escribir el CSV con Python. Precios en la moneda publicada; no convertir.
5. Imprimir un resumen: cantidad, mediana y rango por búsqueda, y compararlo con la corrida
   anterior si existe.
6. Si el supuesto de alquiler o de US$/m² del modelo cambió más de 10%, actualizar la celda
   correspondiente en `contexto/inmuebles/escenarios-deptos.xlsx` (hoja Supuestos) y
   decirlo en el cierre.

## Lo que no se hace

- No contactar inmobiliarias ni completar formularios.
- No descargar archivos ni aceptar términos.
- No usar Apify u otro scraper pago sin que Agustina lo haya activado ella misma.
