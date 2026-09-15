"""Simulación mes a mes de secuencias de compra 2028-2034. Precios planos en USD (sin
apreciación: supuesto explícito). Sale por consola; los números se citan en el análisis."""
from datetime import date
TC, RATE_HOUSE, RATE_C = 1500, 0.115, 0.15
A_VAL, B_VAL, C_PRICE = 145_000, 140_000, 140_000
HOUSE = 95 * 2500
BUY, SELL = 0.08, 0.051
RENT = 900_000 * (11/12) * 0.9 / TC          # 495 neto
S = 3_000                                     # ahorro pareja desde mar-2028: Maxi 2.000 (libera B) + Agustina ~1.000 (Roxom 2.400, sin deuda)
START = (2028, 3); END = (2034, 12)

def pmt(cap, r, n=360): m = r/12; return cap*m/(1-(1+m)**-n)
def months(a, b): return (b[0]-a[0])*12 + (b[1]-a[1])

def run(plan, S=S):
    cash, debt, cuota, rate = 0.0, 0.0, 0.0, 0.0
    props = {"A": True, "B": True, "C": False, "H": False}   # H = casa grande
    live = "A"; log = []; max_cuota = 0
    y, m = START
    while (y, m) <= END:
        rented = sum(1 for k, v in props.items() if v and k != live)
        income = S + RENT * rented
        # pagar cuota y prepagar el resto
        if debt > 0:
            pay = min(debt * (1 + rate/12), income)
            interest = debt * rate/12
            debt = debt + interest - pay
            cash += income - pay
            if debt < 1: debt = 0
        else:
            cash += income
        # decisiones del plan
        for step in plan:
            if step["done"]: continue
            if step["when"](cash, debt, props):
                cash, debt, rate, props, live, note = step["do"](cash, debt, rate, props, live)
                cuota = pmt(debt, rate) if debt else 0; max_cuota = max(max_cuota, cuota)
                step["done"] = True; log.append((f"{y}-{m:02d}", note, round(debt), round(cuota)))
        m += 1
        if m == 13: y += 1; m = 1
    equity = sum(v for k, v in {"A": A_VAL, "B": B_VAL, "C": C_PRICE, "H": HOUSE}.items() if props[k]) - debt + cash
    return log, round(equity), round(debt), round(cash), max_cuota

def sell_a_buy_house(cash, debt, rate, props, live):
    cash += A_VAL * (1 - SELL); props["A"] = False
    need = HOUSE * (1 + BUY); loan = max(0, need - cash); cash = max(0, cash - need)
    props["H"] = True; return cash, debt + loan, RATE_HOUSE, props, "H", f"vende A, compra casa con préstamo US$ {loan:,.0f}"
def buy_house_75(cash, debt, rate, props, live):
    entry = HOUSE * (0.25 + BUY); loan = HOUSE * 0.75; cash -= entry
    props["H"] = True; return cash, debt + loan, RATE_HOUSE if debt == 0 else max(rate, RATE_HOUSE), props, "H", f"compra casa 75% LTV, préstamo US$ {loan:,.0f}"
def buy_c_75(cash, debt, rate, props, live):
    entry = C_PRICE * (0.25 + BUY); loan = C_PRICE * 0.75; cash -= entry
    props["C"] = True; return cash, debt + loan, RATE_C, props, live, f"compra C 75% LTV al 15%, préstamo US$ {loan:,.0f}"
def buy_c_cash(cash, debt, rate, props, live):
    cash -= C_PRICE * (1 + BUY); props["C"] = True
    return cash, debt, rate, props, live, "compra C al contado"

def step(when, do): return {"when": when, "do": do, "done": False}
house_entry = HOUSE * (0.25 + BUY); c_entry = C_PRICE * (0.25 + BUY); c_cash = C_PRICE * (1 + BUY)

plans = {
 "P1 vender A, casa 2028 con préstamo chico, B alquilado, C al contado después": [
    step(lambda c, d, p: True, sell_a_buy_house),
    step(lambda c, d, p: d == 0 and c >= c_cash, buy_c_cash)],
 "P2 no vender: casa 75% LTV con A y B alquilados, C al contado después": [
    step(lambda c, d, p: c >= house_entry, buy_house_75),
    step(lambda c, d, p: d == 0 and c >= c_cash, buy_c_cash)],
 "P3 Maxi: C primero (75% al 15%), casa 75% LTV después": [
    step(lambda c, d, p: c >= c_entry, buy_c_75),
    step(lambda c, d, p: p["C"] and c >= house_entry, buy_house_75)],
 "P4 Agustina: C al contado primero, casa 75% LTV después": [
    step(lambda c, d, p: c >= c_cash, buy_c_cash),
    step(lambda c, d, p: p["C"] and c >= house_entry, buy_house_75)],
}
print(f"Ahorro pareja US$ {S}/mes desde mar-2028; renta neta US$ {RENT:.0f}/unidad; casa US$ {HOUSE:,} (+8%); precios planos.\n")
for name, plan in plans.items():
    log, eq, debt, cash, mc = run(plan)
    print(name)
    for l in log: print(f"   {l[0]}  {l[1]:60s} deuda US$ {l[2]:>8,}  cuota US$ {l[3]:>5,}")
    print(f"   dic-2034: patrimonio US$ {eq:,}  deuda US$ {debt:,}  efectivo US$ {cash:,}  cuota máx US$ {mc:,.0f} -> ingreso demostrable pareja ≥ ${mc*TC/0.25/1e6:,.1f} M\n")
print("Sensibilidad P1 con ahorro 2.300 (Roxom sigue en 1.600):")
log, eq, debt, cash, mc = run([step(lambda c,d,p: True, sell_a_buy_house), step(lambda c,d,p: d==0 and c>=c_cash, buy_c_cash)], S=2300)
for l in log: print(f"   {l[0]}  {l[1]}")
print(f"   dic-2034: patrimonio US$ {eq:,} deuda US$ {debt:,}")
print("\nCarry anual de sostener un depto al 4,2% neto financiado con hipoteca UVA:")
for r in (0.115, 0.15): print(f"   tasa real {r:.1%}: {0.0424-r:+.1%} por año = US$ {(0.0424-r)*140000:,.0f} sobre US$ 140.000")
print(f"Fricción de vender A: US$ {A_VAL*SELL:,.0f} (una vez). Se recupera en {A_VAL*SELL/((0.115-0.0424)*A_VAL/12):.0f} meses de carry.")
