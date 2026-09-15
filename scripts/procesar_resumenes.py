#!/usr/bin/env python3
"""
Procesa resúmenes de tarjeta (Galicia, Santander, BBVA) a dos CSV:

- datos/movimientos.csv  un renglón por consumo
- datos/resumenes.csv    un renglón por resumen: cierre, vencimiento, total, mínimo, pagos,
                         intereses, punitorios, comisiones y percepciones

La regla central: NINGÚN dato sale de acá sin reconciliar contra el total que declara
el propio PDF. Si no reconcilia, el script falla y avisa cuál. Esto existe porque en
agosto 2026 un bug de atribución invirtió los consumos entre titulares y sólo apareció
al validar contra los totales del resumen.

Uso:
    python3 scripts/procesar_resumenes.py                    # procesa frances/ galicia/ santander/
    python3 scripts/procesar_resumenes.py ruta/al.pdf ...    # sólo esos archivos (PDF o xlsx)
    python3 scripts/procesar_resumenes.py --tolerancia 2000  # margen de reconciliación en $
"""
import re, os, sys, csv, glob, argparse
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(RAIZ, "datos", "resumenes-texto")
OUT = os.path.join(RAIZ, "datos", "movimientos.csv")
OUT_RES = os.path.join(RAIZ, "datos", "resumenes.csv")

MES = {"Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,"Julio":7,"Agosto":8,
       "Setiem.":9,"Septiem.":9,"Octubre":10,"Noviem.":11,"Diciem.":12,
       "Ene":1,"Feb":2,"Mar":3,"Abr":4,"May":5,"Jun":6,"Jul":7,"Ago":8,"Sep":9,"Set":9,
       "Oct":10,"Nov":11,"Dic":12}

CAMPOS_RES = ["banco", "tarjeta", "resumen", "archivo", "cierre", "vencimiento",
              "prox_cierre", "prox_vto", "total_ars", "total_usd", "minimo_ars",
              "pagos_ars", "pagos_usd", "consumos_ars", "intereses_ars", "punitorios_ars",
              "comisiones_ars", "percepciones_ars"]

# Importe argentino: 1.234,56 o 1234,56. Los lookarounds evitan tomar "78,00" de una tasa
# "78,000" o de un tipo de cambio "TC1510,000". Santander marca los créditos con "-" al final.
IMPORTE = re.compile(r"(?<![\d,])(-?[\d.]*\d,\d{2})(?!\d)(-?)")


def num(s):
    """Acepta negativos: los reintegros vienen con signo y el PDF los netea en el total."""
    return float(s.replace(".", "").replace(",", "."))


def importes(linea):
    """Todos los importes de una línea, con el signo de Santander (menos al final) aplicado."""
    return [-abs(num(a)) if m == "-" else num(a) for a, m in IMPORTE.findall(linea)]


def fecha_iso(dd, mes, yy):
    """dd + mes (número o abreviatura) + año de 2 o 4 dígitos -> AAAA-MM-DD."""
    m = MES[mes] if mes in MES else int(mes)
    y = int(yy) if len(str(yy)) == 4 else 2000 + int(yy)
    return f"{y}-{m:02d}-{int(dd):02d}"


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
# La Mastercard de Galicia usa otro formato: fecha con mes en letras (29-Jul-26) y
# comprobante de 5 dígitos. Sin este patrón devolvía 0 movimientos sin avisar.
GAL_MC = re.compile(r"^(\d{2})-([A-Za-z]{3})-(\d{2})\s+(.+?)\s+(\d{5,6})\s+"
                    r"(-?[\d.]+,\d{2})\s*(-?[\d.]+,\d{2})?\s*$")
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
        if g:
            d, _, com, cuota, cbte, a, b = g.groups()
            dd, mm, yy = d.split("-")
            fecha = f"20{yy}-{mm}-{dd}"
        else:
            g = GAL_MC.match(line.strip()) if tipo == "MASTERCARD" else None
            if not g or g.group(2) not in MES:
                continue
            dd, mon, yy, com, cbte, a, b = g.groups()
            cuota, fecha = None, fecha_iso(dd, mon, yy)
        com, usd = com.strip(), None
        mu = GAL_FX.search(com)
        if mu:
            usd = num(mu.group(1)); com = GAL_FX.sub("", com).strip()
        pesos = num(a) if a else None
        if b:
            usd = num(b)
        # Consumo en el exterior de la Mastercard: "JETSMART(URY,USD, 2155,89) 00936 2.155,89".
        # El único importe es la columna DÓLARES, no pesos.
        fx = re.search(r"\(([A-Z]{3}),([A-Z]{3}),\s*[\d.,]+\)", com)
        if fx and not b:
            usd, pesos = pesos, None
            com = com[:fx.start()].strip()
        # La Mastercard no separa por titular: todo es de Agustina.
        filas.append(dict(banco="Galicia", tarjeta=tipo, resumen=resumen,
                          fecha=fecha, comercio=com, cuota=cuota, comprobante=cbte,
                          pesos=pesos, usd=usd,
                          titular="Agustina" if tipo == "MASTERCARD" else None))
        if tipo != "MASTERCARD":
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


def _xlsx_monto(v):
    """'$-215.000,00' / 'U$S19,99' -> float. Vacío o '-' -> None."""
    if v in (None, "", "-"):
        return None
    return num(str(v).replace("U$S", "").replace("$", "").strip())


def parse_santander_xlsx(path):
    """Santander entrega "Último resumen" en xlsx desde septiembre 2026.

    Devuelve (movimientos, totales declarados, datos del resumen). El xlsx trae el
    total de cada tarjeta ("Total de ... terminada en NNNN") y se valida contra eso,
    igual que un PDF.
    """
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = [list(r) + [None] * 6 for r in ws.iter_rows(values_only=True)]
    txt0 = lambda r: str(r[0] or "")
    tipo = "AMEX" if any("American Express" in txt0(r) for r in rows[:4]) else "VISA"

    d = dict(banco="Santander", tarjeta=tipo, archivo=os.path.basename(path))
    filas, declarado, bloque, ult_fecha = [], 0.0, None, None
    for i, r in enumerate(rows):
        c0 = txt0(r)
        if c0 == "Fecha de cierre":
            d["cierre"] = fecha_iso(*rows[i + 1][0].split("/"))
            d["vencimiento"] = fecha_iso(*rows[i + 1][1].split("/"))
        elif c0 == "Total a pagar":
            d["total_ars"], d["total_usd"] = _xlsx_monto(rows[i + 1][0]), _xlsx_monto(rows[i + 1][1])
        elif c0 == "Mínimo a pagar":
            d["minimo_ars"] = _xlsx_monto(rows[i + 1][0])
        elif c0.startswith("Cierre:") and str(r[1] or "").startswith("Cierre:"):
            d["prox_cierre"] = fecha_iso(*r[1].split(":")[1].strip().split("/"))
        elif c0.startswith("Vencimiento:") and str(r[1] or "").startswith("Vencimiento:"):
            d["prox_vto"] = fecha_iso(*r[1].split(":")[1].strip().split("/"))
        elif c0.startswith("Tarjeta de ") and "terminada en" in c0:
            bloque = "consumos"; ult_fecha = None
        elif c0 == "Pago de tarjeta y devoluciones":
            bloque = "pagos"; ult_fecha = None
        elif c0 == "Otros conceptos":
            bloque = "otros"
        elif c0.startswith("Total de ") and "terminada en" in c0:
            declarado += _xlsx_monto(r[4]) or 0.0
            bloque = None
        elif c0 == "Fecha" or c0 == "Descripción":
            continue
        elif bloque in ("consumos", "pagos") and r[1]:
            fecha = c0 or ult_fecha
            ult_fecha = fecha
            desc = str(r[1]).strip()
            pesos, usd = _xlsx_monto(r[4]), _xlsx_monto(r[5])
            if bloque == "pagos":
                low = desc.lower()
                if "pago" in low:
                    k = "pagos_usd" if "usd" in low else "pagos_ars"
                    d[k] = d.get(k, 0.0) + ((usd if k == "pagos_usd" else pesos) or 0.0)
                elif "5617" in low or "4815" in low:
                    d["percepciones_ars"] = d.get("percepciones_ars", 0.0) + (pesos or 0.0)
                continue
            cm = re.match(r"(\d+) de (\d+)", str(r[2] or ""))
            filas.append(dict(banco="Santander", tarjeta=tipo, resumen=None,
                              fecha=fecha_iso(*fecha.split("/")), comercio=desc,
                              cuota=f"{int(cm.group(1)):02d}/{int(cm.group(2)):02d}" if cm else None,
                              comprobante=str(r[3] or "").strip() or None,
                              pesos=pesos, usd=usd, titular="Agustina"))
        elif bloque == "otros" and r[1]:
            low, monto = c0.lower(), _xlsx_monto(r[1]) or 0.0
            if "interes" in low and "punit" in low:
                d["punitorios_ars"] = d.get("punitorios_ars", 0.0) + monto
            elif "interes" in low:
                d["intereses_ars"] = d.get("intereses_ars", 0.0) + monto
            elif "5617" in low or "4815" in low:
                d["percepciones_ars"] = d.get("percepciones_ars", 0.0) + monto
            elif "comision" in low:
                d["comisiones_ars"] = d.get("comisiones_ars", 0.0) + monto

    d["resumen"] = d.get("vencimiento", os.path.basename(path))
    d["consumos_ars"] = declarado
    for f in filas:
        f["resumen"] = d["resumen"]
    return filas, {"Agustina": declarado}, d


# ------------------------------------------------------- datos del resumen
def clave_resumen(banco, base, txt):
    """(tarjeta, resumen) con el mismo criterio que los parsers, aunque no haya consumos."""
    if banco == "Galicia":
        m = re.search(r"(?:VISA|MAST)(\d{1,2})_(\d{1,2})_(\d{4})", base)
        tarjeta = "VISA" if "VISA" in base.upper() else "MASTERCARD"
        return tarjeta, (f"{int(m.group(3))}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else base)
    if banco == "Santander":
        m = re.search(r"-(\d{2})-(\d{2})-(\d{4})", base)
        tarjeta = "AMEX" if "AMEX" in base.upper() else "VISA"
        return tarjeta, (f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else base)
    m = re.search(r"CIERRE ACTUAL\n(\d{2})-([A-Za-z]{3})-(\d{2})", txt)
    return "VISA", (f"20{m.group(3)}-{MES[m.group(2)]:02d}-{m.group(1)}" if m else base)


def datos_resumen(banco, tarjeta, resumen, archivo, txt):
    """Lo que hace falta para seguir la deuda mes a mes. Sale de la cabecera del PDF."""
    d = dict(banco=banco, tarjeta=tarjeta, resumen=resumen, archivo=archivo)
    lineas = [l.strip() for l in txt.splitlines()]

    def sumar(clave, valor):
        d[clave] = round(d.get(clave, 0.0) + valor, 2)

    if banco == "Galicia":
        F = r"(\d{2})-([A-Za-z]{3})-(\d{2})"
        m = re.search(r"\s+".join([F] * 6), txt)
        if m:
            g = m.groups()
            d["cierre"], d["vencimiento"] = fecha_iso(*g[6:9]), fecha_iso(*g[9:12])
            d["prox_cierre"], d["prox_vto"] = fecha_iso(*g[12:15]), fecha_iso(*g[15:18])
        m = re.search(r"TOTAL A PAGAR\s+(-?[\d.]+,\d{2})\s+(-?[\d.]+,\d{2})", txt)
        if m:
            d["total_ars"], d["total_usd"] = num(m.group(1)), num(m.group(2))
        m = re.search(r"PAGO MINIMO.*?\$\s*(-?[\d.]+,\d{2})", txt, re.S)
        if m:
            d["minimo_ars"] = num(m.group(1))
        # El bloque CONSOLIDADO va de SALDO ANTERIOR a TOTAL A PAGAR y aparece una sola vez.
        ini = next((i for i, l in enumerate(lineas) if l.startswith("SALDO ANTERIOR")), None)
        fin = next((i for i, l in enumerate(lineas) if l.startswith("TOTAL A PAGAR")), None)
        bloque = lineas[ini:fin] if ini is not None and fin is not None and fin > ini else []
        for l in bloque:
            imp = importes(l)
            if not imp:
                continue
            if "SU PAGO" in l:
                sumar("pagos_usd" if ("USD" in l or "U$S" in l) else "pagos_ars", imp[0])
            elif l.startswith("INTERESES PUNITORIOS"):
                sumar("punitorios_ars", imp[0])
            elif l.startswith("INTERESES"):
                sumar("intereses_ars", imp[0])
            elif "COMISION" in l:
                sumar("comisiones_ars", imp[0])
        for l in lineas:
            if re.search(r"RG\.?\s*(5617|4815)", l) and importes(l):
                sumar("percepciones_ars", importes(l)[-1])
        tc = [num(x) for x in re.findall(r"Total Consumos de [A-ZÁ-Ú ]+?\s+([\d.]+,\d{2})", txt)]
        mc = re.search(r"TOTAL CONSUMOS DEL MES\s+(-?[\d.]+,\d{2})", txt)
        d["consumos_ars"] = sum(tc) if tc else (num(mc.group(1)) if mc else None)

    elif banco == "Santander":
        m = re.search(r"CIERRE\s+(\d{2}) (\w{3}) (\d{2})\s*VENCIMIENTO\s+(\d{2}) (\w{3}) (\d{2})", txt)
        if m:
            d["cierre"], d["vencimiento"] = fecha_iso(*m.groups()[:3]), fecha_iso(*m.groups()[3:])
        m = re.search(r"Prox\.Cierre:\s+(\d{2}) (\w{3}) (\d{2})\s+Prox\.Vto\.:\s+(\d{2}) (\w{3}) (\d{2})", txt)
        if m:
            d["prox_cierre"], d["prox_vto"] = fecha_iso(*m.groups()[:3]), fecha_iso(*m.groups()[3:])
        # Saldo: última línea con "TNA ... TEM"; el mínimo es el primer importe que sigue.
        idx = [i for i, l in enumerate(lineas) if l.startswith("TNA") and "TEM" in l and importes(l)]
        if idx:
            imp = importes(lineas[idx[-1]])
            d["total_ars"], d["total_usd"] = (imp[-2], imp[-1]) if len(imp) >= 2 else (imp[-1], None)
            sig = next((importes(l) for l in lineas[idx[-1] + 1:] if importes(l)), None)
            if sig:
                d["minimo_ars"] = sig[0]
        for l in lineas:
            imp = importes(l)
            if not imp:
                continue
            if "SU PAGO EN USD" in l:
                sumar("pagos_usd", -abs(imp[0]))
            elif "SU PAGO" in l:
                sumar("pagos_ars", imp[0])
            elif re.search(r"RG\.?\s*(5617|4815)", l):
                sumar("percepciones_ars", imp[-1])
            elif "INTERESES PUNITORIOS" in l:
                sumar("punitorios_ars", imp[-1])
            elif "INTERESES" in l and "FINANCIACION" in l:
                sumar("intereses_ars", imp[-1])
            elif "COMISION" in l:
                sumar("comisiones_ars", imp[-1])
        tot = totales_declarados("Santander", txt)
        d["consumos_ars"] = tot.get("Agustina")

    elif banco == "BBVA":
        def campo(etq):
            m = re.search(etq + r"\n(-?[\d.]+,\d{2})", txt)
            return num(m.group(1)) if m else None
        def fecha_campo(etq):
            m = re.search(etq + r"\n(\d{2})-([A-Za-z]{3})-(\d{2})", txt)
            return fecha_iso(*m.groups()) if m else None
        d["cierre"], d["vencimiento"] = fecha_campo("CIERRE ACTUAL"), fecha_campo("VENCIMIENTO ACTUAL")
        d["prox_cierre"], d["prox_vto"] = fecha_campo("PRÓXIMO CIERRE"), fecha_campo("PRÓXIMO VENCIMIENTO")
        d["total_ars"], d["total_usd"] = campo(r"SALDO ACTUAL \$"), campo(r"SALDO ACTUAL U\$S")
        d["minimo_ars"] = campo(r"PAGO MÍNIMO \$")
        # El consolidado (SALDO ANTERIOR -> SALDO ACTUAL) se repite en el detalle: sólo el primero.
        ini = next((i for i, l in enumerate(lineas) if l.startswith("SALDO ANTERIOR")), None)
        fin = next((i for i, l in enumerate(lineas) if ini is not None and i > ini
                    and l.startswith("SALDO ACTUAL")), None)
        for l in (lineas[ini:fin] if ini is not None and fin is not None else []):
            imp = importes(l)
            if not imp:
                continue
            if "SU PAGO" in l:
                sumar("pagos_usd" if "USD" in l else "pagos_ars", imp[0])
            elif "PUNITORIO" in l:
                sumar("punitorios_ars", imp[0])
            elif "INTERES" in l:
                sumar("intereses_ars", imp[0])
            elif "COMISION" in l:
                sumar("comisiones_ars", imp[0])
            elif re.search(r"RG\.?\s*(5617|4815)", l):
                sumar("percepciones_ars", imp[-1])
        d["consumos_ars"] = totales_declarados("BBVA", txt).get("Agustina")
    return d


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
        if not out:
            # Mastercard: no separa por titular, declara un único total del mes.
            m = re.search(r"TOTAL CONSUMOS DEL MES\s+(-?[\d.]+,\d{2})", txt)
            if m:
                out["Agustina"] = num(m.group(1))
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


def fusionar(ruta, nuevas, campos, clave):
    """Reemplaza sólo los resúmenes reprocesados. La clave es (banco, tarjeta, resumen):
    con la fecha sola, reprocesar la VISA de Santander borraba la AMEX del mismo día."""
    previas = []
    if os.path.exists(ruta):
        with open(ruta) as fh:
            previas = list(csv.DictReader(fh))
    procesados = {clave(r) for r in nuevas}
    conservadas = [r for r in previas if clave(r) not in procesados]
    return conservadas, conservadas + [{k: ("" if r.get(k) is None else r[k]) for k in campos}
                                       for r in nuevas]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*", help="PDF o xlsx; sin argumentos procesa las tres carpetas")
    ap.add_argument("--tolerancia", type=float, default=1500,
                    help="margen en $ para dar por reconciliado un resumen")
    args = ap.parse_args()

    archivos = args.pdfs or sorted(
        glob.glob(os.path.join(RAIZ, "frances", "*.pdf")) +
        glob.glob(os.path.join(RAIZ, "galicia", "*.pdf")) +
        glob.glob(os.path.join(RAIZ, "santander", "*.pdf")) +
        glob.glob(os.path.join(RAIZ, "santander", "*.xlsx")))
    if not archivos:
        sys.exit("No encontré resúmenes.")
    # Los PDF primero: si el mismo resumen está en PDF y en xlsx, manda el PDF.
    archivos = sorted(archivos, key=lambda p: p.lower().endswith(".xlsx"))

    todas, fallas, sin_totales, resumenes = [], [], [], []
    for arch in archivos:
        base = os.path.basename(arch)
        if arch.lower().endswith(".xlsx"):
            filas, decl, d = parse_santander_xlsx(arch)
            clave = (d["banco"], d["tarjeta"], d["resumen"])
            if any((r["banco"], r["tarjeta"], r["resumen"]) == clave for r in resumenes):
                print(f"  {'Santander':10} {base[:48]:50} (ya está en PDF, se omite el xlsx)")
                continue
            banco = "Santander"
        else:
            ruta_txt = extraer_texto(arch, TXT)
            txt = open(ruta_txt).read()
            banco = detectar_banco(txt)
            if not banco:
                fallas.append(f"  {base}: no pude detectar el banco")
                continue
            filas = {"Galicia": parse_galicia, "Santander": parse_santander,
                     "BBVA": parse_bbva}[banco](arch, txt)
            decl = totales_declarados(banco, txt)
            tarjeta, resumen = clave_resumen(banco, base, txt)
            d = datos_resumen(banco, tarjeta, resumen, base, txt)
        if not decl:
            sin_totales.append(f"  {base}: el resumen no declara totales, no se pudo validar")
        else:
            fallas += validar(filas, decl, base, args.tolerancia)
        todas += filas
        resumenes.append(d)
        print(f"  {banco:10} {base[:48]:50} {len(filas):4d} movimientos")

    # dedupe
    visto, limpias = set(), []
    for r in todas:
        k = (r["banco"], r["tarjeta"], r["resumen"], r["fecha"], r["comercio"],
             r["comprobante"], r["pesos"], r["usd"])
        if k in visto:
            continue
        visto.add(k); limpias.append(r)

    print(f"\n{len(limpias)} movimientos únicos de {len(archivos)} resúmenes")

    if sin_totales:
        print("\nSIN VALIDAR (el resumen no declara totales):")
        print("\n".join(sin_totales))

    if fallas:
        print("\n*** NO RECONCILIA — no se escribió ningún CSV ***")
        print("\n".join(fallas))
        print("\nArreglá el parser antes de usar estos datos. Un total que no cierra suele")
        print("significar atribución cruzada entre titulares, no un redondeo.")
        sys.exit(1)

    # Merge con lo que ya estaba: correr un subconjunto NO puede pisar el CSV entero.
    campos = ["fecha", "banco", "tarjeta", "titular", "comercio",
              "cuota", "pesos", "usd", "resumen", "comprobante"]
    clave = lambda r: (r.get("banco"), r.get("tarjeta"), r.get("resumen"))
    conservadas, limpias = fusionar(OUT, limpias, campos, clave)
    if conservadas:
        print(f"Conservo {len(conservadas)} movimientos de resúmenes no reprocesados")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(limpias, key=lambda r: (r["fecha"], r["banco"])))

    _, res = fusionar(OUT_RES, resumenes, CAMPOS_RES, clave)
    with open(OUT_RES, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS_RES, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(res, key=lambda r: (str(r["cierre"] or r["resumen"]), r["banco"], r["tarjeta"])))
    print(f"\nOK — todo reconcilia. Escrito en {OUT} y {OUT_RES}")


if __name__ == "__main__":
    main()
