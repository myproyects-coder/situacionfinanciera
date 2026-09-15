#!/usr/bin/env python3
"""
Procesa resúmenes de tarjeta (Galicia, Santander, BBVA) a un CSV de movimientos.

La regla central: NINGÚN dato sale de acá sin reconciliar contra el total que declara
el propio PDF. Si no reconcilia, el script falla y avisa cuál. Esto existe porque en
agosto 2026 un bug de atribución invirtió los consumos entre titulares y sólo apareció
al validar contra los totales del resumen.

Uso:
    python3 scripts/procesar_resumenes.py                    # procesa frances/ galicia/ santander/
    python3 scripts/procesar_resumenes.py ruta/al.pdf ...    # sólo esos archivos
    python3 scripts/procesar_resumenes.py --tolerancia 2000  # margen de reconciliación en $
"""
import re, os, sys, csv, glob, argparse
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(RAIZ, "datos", "resumenes-texto")
OUT = os.path.join(RAIZ, "datos", "movimientos.csv")

MES = {"Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,"Julio":7,"Agosto":8,
       "Setiem.":9,"Septiem.":9,"Octubre":10,"Noviem.":11,"Diciem.":12,
       "Ene":1,"Feb":2,"Mar":3,"Abr":4,"May":5,"Jun":6,"Jul":7,"Ago":8,"Sep":9,"Set":9,
       "Oct":10,"Nov":11,"Dic":12}

def num(s):
    """Acepta negativos: los reintegros vienen con signo y el PDF los netea en el total."""
    return float(s.replace(".", "").replace(",", "."))


def extraer_texto(pdf, destino):
    """PDF -> .txt en disco. El texto crudo nunca vuelve al contexto del modelo."""
    import pypdf
    r = pypdf.PdfReader(pdf)
    txt = "\n".join(f"--- page {i+1} ---\n" + (p.extract_text() or "")
                    for i, p in enumerate(r.pages))
    os.makedirs(destino, exist_ok=True)
    salida = os.path.join(destino, re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(pdf)) + ".txt")
    open(salida, "w").write(txt)
    return salida


def detectar_banco(txt):
    if "Tarjeta Crédito" in txt and "Galicia" in txt or "bancogalicia" in txt:
        return "Galicia"
    if "Santander" in txt:
        return "Santander"
    if "BBVA" in txt:
        return "BBVA"
    return None


# ----------------------------------------------------------------- parsers
GAL = re.compile(r"^(\d{2}-\d{2}-\d{2})\s+([*KFE]?)\s*(.+?)\s+(?:(\d{2}/\d{2})\s+)?(\d{6})\s+"
                 r"(-?[\d.]+,\d{2})?\s*(-?[\d.]+,\d{2})?\s*$")
GAL_FX = re.compile(r"(?:USD|U\$S|EUR)\s+([\d.]+,\d{2})")
SAN_MES = re.compile(r"^(\d{2})\s+([A-ZÁ-Ú][a-zá-ú]+\.?)\s+(\d{2})\s+(\d{6})\s+([*KFE]?)\s+(.*)$")
SAN_DIA = re.compile(r"^\s+(\d{2})\s+(\d{6})\s+([*KFE]?)\s+(.*)$")
SAN_TAIL = re.compile(r"^(.*?)\s{2,}(?:C\.(\d{2}/\d{2}))?\s*(-?[\d.]+,\d{2})?\s*(-?[\d.]+,\d{2})?\s*$")
SAN_FX = re.compile(r"(USD|U\$S|EUR|BRL)\s+([\d.]+,\d{2})")
BBV = re.compile(r"^(\d{2})-([A-Za-z]{3})-(\d{2})\s+(.+?)\s+(\d{6})\s+(-?[\d.]+,\d{2})\s*(-?[\d.]+,\d{2})?\s*$")


def parse_galicia(path, txt):
    base = os.path.basename(path)
    tipo = "VISA" if "VISA" in base.upper() else "MASTERCARD"
    m = re.search(r"(?:VISA|MAST)(\d{1,2})_(\d{1,2})_(\d{4})", base)
    resumen = f"{int(m.group(3))}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else base
    filas, pend = [], []
    for line in txt.splitlines():
        if "Total Consumos de" in line:
            up = line.upper()
            t = ("Maximiliano (adicional)" if "MAXIMILIANO" in up else
                 "Amir (adicional)" if "AMIR" in up else
                 "Agustina" if "AGUSTINA" in up else "Otro adicional")
            for r in pend:
                r["titular"] = t          # el marcador CIERRA el bloque anterior
            pend = []
            continue
        g = GAL.match(line.strip())
        if not g:
            continue
        d, _, com, cuota, cbte, a, b = g.groups()
        com, usd = com.strip(), None
        mu = GAL_FX.search(com)
        if mu:
            usd = num(mu.group(1)); com = GAL_FX.sub("", com).strip()
        pesos = num(a) if a else None
        if b:
            usd = num(b)
        dd, mm, yy = d.split("-")
        filas.append(dict(banco="Galicia", tarjeta=tipo, resumen=resumen,
                          fecha=f"20{yy}-{mm}-{dd}", comercio=com, cuota=cuota,
                          comprobante=cbte, pesos=pesos, usd=usd, titular=None))
        pend.append(filas[-1])
    return filas


def parse_santander(path, txt):
    base = os.path.basename(path)
    tipo = "AMEX" if "AMEX" in base.upper() else "VISA"
    m = re.search(r"-(\d{2})-(\d{2})-(\d{4})", base)
    resumen = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else base
    filas, cur = [], None
    for line in txt.splitlines():
        g = SAN_MES.match(line.rstrip())
        if g:
            yy, mes, dia, cbte, _, rest = g.groups(); cur = (yy, mes)
        else:
            g = SAN_DIA.match(line.rstrip())
            if not g or cur is None:
                continue
            dia, cbte, _, rest = g.groups(); yy, mes = cur
        if mes not in MES:
            continue
        t = SAN_TAIL.match(rest)
        if not t:
            continue
        com, cuota, a, b = t.groups()
        com, usd, pesos = com.strip(), None, None
        mu = SAN_FX.search(com)
        if mu:
            usd = num(mu.group(2)); com = SAN_FX.sub("", com).strip()
        # Consumo en moneda extranjera: el comercio termina con el codigo de moneda
        # (a veces pegado, ej "MX5WY31KXUSD"). Ahi el primer importe es la moneda
        # original -BRL, EUR, USD- y el segundo el equivalente en dolares. Ninguno
        # de los dos es pesos. Sin esto, los consumos en Brasil entraban como ARS.
        if re.search(r"(USD|U\$S|EUR|BRL)$", com):
            usd = num(b) if b else (num(a) if a else None)
            com = re.sub(r"\s*(USD|U\$S|EUR|BRL)$", "", com).strip()
        else:
            pesos = num(a) if a else None
            if b:
                usd = num(b)
            if usd is not None and pesos is not None and abs(pesos - usd) < 0.001:
                pesos = None
        if pesos is None and usd is None:
            continue
        filas.append(dict(banco="Santander", tarjeta=tipo, resumen=resumen,
                          fecha=f"20{yy}-{MES[mes]:02d}-{dia}", comercio=com, cuota=cuota,
                          comprobante=cbte, pesos=pesos, usd=usd, titular="Agustina"))
    return filas


def parse_bbva(path, txt):
    m = re.search(r"CIERRE ACTUAL\n(\d{2})-([A-Za-z]{3})-(\d{2})", txt)
    resumen = f"20{m.group(3)}-{MES[m.group(2)]:02d}-{m.group(1)}" if m else os.path.basename(path)
    filas = []
    for line in txt.splitlines():
        g = BBV.match(line.strip())
        if not g:
            continue
        dd, mon, yy, com, cbte, a, b = g.groups()
        if mon not in MES:
            continue
        com, usd = com.strip(), None
        mu = SAN_FX.search(com)
        if mu:
            usd = num(mu.group(2)); com = SAN_FX.sub("", com).strip()
        pesos = num(a)
        if b:
            usd = num(b)
        if usd is not None and abs(pesos - usd) < 0.001:
            pesos = None
        filas.append(dict(banco="BBVA", tarjeta="VISA", resumen=resumen,
                          fecha=f"20{yy}-{MES[mon]:02d}-{dd}", comercio=com, cuota=None,
                          comprobante=cbte, pesos=pesos, usd=usd, titular="Agustina"))
    return filas


# ------------------------------------------------------------- validación
def totales_declarados(banco, txt):
    """Lo que el PDF dice que suman los consumos. Es la vara contra la que se valida."""
    out = {}
    if banco == "Galicia":
        for m in re.finditer(r"Total Consumos de ([A-ZÁ-Ú ]+?)\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})", txt):
            nom = m.group(1).strip().upper()
            t = ("Maximiliano (adicional)" if "MAXIMILIANO" in nom else
                 "Amir (adicional)" if "AMIR" in nom else
                 "Agustina" if "AGUSTINA" in nom else "Otro adicional")
            out[t] = num(m.group(2))
    elif banco == "Santander":
        # Puede haber MAS DE UNA tarjeta en el mismo resumen (ej. 7403 y 8494 en agosto
        # 2026), cada una con su propio "Total Consumos". Hay que sumarlas todas: comparar
        # contra una sola hacia fallar la reconciliacion con el parser funcionando bien.
        tot = 0.0; encontrado = False
        for m in re.finditer(r"Total Consumos de\s+(?:AGUSTINA SOL LOYOLA|[\d ]+?)\s+"
                             r"([\d.]+,\d{2})\s*\*", txt):
            tot += num(m.group(1)); encontrado = True
        if encontrado:
            out["Agustina"] = tot
    elif banco == "BBVA":
        m = re.search(r"TOTAL CONSUMOS DE AGUSTINA SOL LOYOLA\s+([\d.]+,\d{2})", txt)
        if m:
            out["Agustina"] = num(m.group(1))
    return out


def validar(filas, declarados, etiqueta, tol):
    """Devuelve lista de discrepancias. Vacía = reconcilia."""
    obtenido = defaultdict(float)
    for r in filas:
        obtenido[r["titular"] or "sin titular"] += r["pesos"] or 0
    fallas = []
    for tit, esperado in declarados.items():
        got = obtenido.get(tit, 0.0)
        if abs(got - esperado) > tol:
            fallas.append(f"  {etiqueta} | {tit}: PDF dice {esperado:,.2f} / parseado {got:,.2f} "
                          f"(dif {got-esperado:+,.2f})")
    return fallas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--tolerancia", type=float, default=1500,
                    help="margen en $ para dar por reconciliado un resumen")
    args = ap.parse_args()

    pdfs = args.pdfs or sorted(
        glob.glob(os.path.join(RAIZ, "frances", "*.pdf")) +
        glob.glob(os.path.join(RAIZ, "galicia", "*.pdf")) +
        glob.glob(os.path.join(RAIZ, "santander", "*.pdf")))
    if not pdfs:
        sys.exit("No encontré PDFs.")

    todas, fallas, sin_totales = [], [], []
    for pdf in pdfs:
        ruta_txt = extraer_texto(pdf, TXT)
        txt = open(ruta_txt).read()
        banco = detectar_banco(txt)
        if not banco:
            fallas.append(f"  {os.path.basename(pdf)}: no pude detectar el banco")
            continue
        filas = {"Galicia": parse_galicia, "Santander": parse_santander,
                 "BBVA": parse_bbva}[banco](pdf, txt)
        decl = totales_declarados(banco, txt)
        if not decl:
            sin_totales.append(f"  {os.path.basename(pdf)}: el PDF no declara totales, no se pudo validar")
        else:
            fallas += validar(filas, decl, os.path.basename(pdf), args.tolerancia)
        todas += filas
        print(f"  {banco:10} {os.path.basename(pdf)[:48]:50} {len(filas):4d} movimientos")

    # dedupe
    visto, limpias = set(), []
    for r in todas:
        k = (r["banco"], r["tarjeta"], r["resumen"], r["fecha"], r["comercio"],
             r["comprobante"], r["pesos"], r["usd"])
        if k in visto:
            continue
        visto.add(k); limpias.append(r)

    print(f"\n{len(limpias)} movimientos únicos de {len(pdfs)} resúmenes")

    if sin_totales:
        print("\nSIN VALIDAR (el PDF no declara totales):")
        print("\n".join(sin_totales))

    if fallas:
        print("\n*** NO RECONCILIA — el CSV NO se escribió ***")
        print("\n".join(fallas))
        print("\nArreglá el parser antes de usar estos datos. Un total que no cierra suele")
        print("significar atribución cruzada entre titulares, no un redondeo.")
        sys.exit(1)

    # Merge con lo que ya estaba: correr un subconjunto NO puede pisar el CSV entero.
    campos = ["fecha", "banco", "tarjeta", "titular", "comercio",
              "cuota", "pesos", "usd", "resumen", "comprobante"]
    previas = []
    if os.path.exists(OUT):
        with open(OUT) as fh:
            previas = list(csv.DictReader(fh))
    procesados = {r["resumen"] for r in limpias}
    conservadas = [r for r in previas if r.get("resumen") not in procesados]
    if conservadas:
        print(f"Conservo {len(conservadas)} movimientos de resúmenes no reprocesados")
    limpias = conservadas + [{k: ("" if r.get(k) is None else r[k]) for k in campos} for r in limpias]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(limpias, key=lambda r: (r["fecha"], r["banco"])))
    print(f"\nOK — todo reconcilia. Escrito en {OUT}")


if __name__ == "__main__":
    main()
