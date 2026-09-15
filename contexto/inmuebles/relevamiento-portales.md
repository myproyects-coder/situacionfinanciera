# Cómo conectar los portales inmobiliarios — qué hay de verdad y qué no

Verificado el 7 de septiembre de 2026.

## No existe un MCP oficial de ningún portal argentino

Zonaprop, Argenprop, Properati y Mercado Libre Inmuebles no publican servidores MCP. El
registro de conectores no devuelve nada para inmuebles. La API pública de Mercado Libre
responde **403** sin token de aplicación registrada, y los tres portales devuelven 403 a
cualquier pedido por `curl`.

Hay tres caminos reales, en orden de costo:

### 1. El navegador integrado de Claude (gratis, ya funciona)

Probado hoy: el navegador de la app abre Zonaprop y lee los listados sin bloqueo. Con eso
se puede relevar una búsqueda concreta y volcarla a `datos/inmuebles/AAAA-MM-DD.csv`.
No hace falta instalar nada. El skill `relevar-inmuebles` deja el procedimiento fijo.

Límite: es manual (se corre en una sesión), unas 20-30 publicaciones por página. Sirve para
una serie mensual de Caballito, no para bajar 1.500 avisos.

### 2. Apify vía MCP (pago, automatizable)

Apify tiene un servidor MCP oficial (`mcp.apify.com`, o local con
`npx @apify/actors-mcp-server`) y en su tienda hay scrapers de Zonaprop y Argenprop.
Requiere:

- Crear cuenta en Apify y generar un token. **Eso lo hacés vos; Claude no crea cuentas.**
- Node.js 18+ si se usa la versión local (hoy no hay `node` ni `npx` en esta Mac). La
  versión hosteada no lo necesita.
- Agregar a `.mcp.json` del proyecto:

```json
{
  "mcpServers": {
    "apify": {
      "type": "http",
      "url": "https://mcp.apify.com/?actors=ecomscrape/zonaprop-property-listings-scraper,scrapyx/argenprop-properties-scraper",
      "headers": { "Authorization": "Bearer ${APIFY_TOKEN}" }
    }
  }
}
```

Costo: los actores cobran por resultado o por evento; el plan gratuito de Apify da un
crédito mensual chico que alcanza para pruebas. Antes de pagar, revisar que los términos
de uso de cada portal permitan el scraping para uso personal.

### 3. API oficial de Mercado Libre (gratis, con trámite)

Mercado Libre sí tiene API pública (`developers.mercadolibre.com.ar`). Hay que registrar
una aplicación y obtener un token OAuth; con eso `sites/MLA/search?category=MLA1459` devuelve
inmuebles con precio, m², ambientes y ubicación. Cubre sólo lo publicado en ML, que en
Caballito es menos que Zonaprop. Es la única vía que no tiene zona gris legal.

## Recomendación de arranque

Camino 1 este mes, con el skill. Si en dos relevamientos queda claro que hace falta serie
diaria o más volumen, recién ahí Apify. La API de ML se suma cuando haya token.

## Qué se releva y para qué

| Búsqueda | Sirve para |
|---|---|
| 2 amb alquiler Caballito, 50-70 m² | el supuesto de renta de B y de C |
| 2 amb venta Caballito, 55-70 m² | valuación de A y B, precio de C |
| 3-4 amb venta Caballito, 80-110 m² | precio del "uno grande" del escenario 2 |

Cada corrida guarda: fecha, portal, operación, ambientes, m², precio, moneda, expensas,
dirección aproximada, zona, URL. Con seis meses de serie se puede ver la tendencia propia
en vez de fiarse del índice de Zonaprop.
