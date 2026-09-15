"""Simulación 2028-2034 con métrica de Maxi: m² y unidades en propiedad. Precios planos."""
import math
TC=1500; S=3000; RENT=495; M2=65; HOUSE_M2=95
A_VAL,B_VAL,U=145000,140000,140000; HOUSE=95*2500; BUY,SELL=0.08,0.051
R_H,R_U=0.115,0.15
def pmt(c,r,n=360): m=r/12; return c*m/(1-(1+m)**-n)
def sim(name, live_rent, sell_a, house_when, unit_rule, horizon=(2034,12)):
    """live_rent: US$ alquiler que pagan por vivir (0 si viven en propio). sell_a: vender A en mar-2028.
    house_when: 'first' compra casa apenas puede (75% o con lo de A); None nunca.
    unit_rule: ('lev', ltv) compra unidades apalancadas cuando hay entrada; ('cash',) al contado; None nunca."""
    cash=0.0; debts=[]  # [saldo, tasa]
    units={"A":True,"B":True}; house=False; extra=0; log=[]; y,m=2028,3; live="A"
    if sell_a: cash+=A_VAL*(1-0.036); units["A"]=False
    while (y,m)<=horizon:
        rented=sum(units.values())+extra-(0 if live_rent or house else 1)
        income=S+RENT*max(rented,0)-live_rent
        # cuotas + prepago sobre la deuda más cara
        pay=income
        debts.sort(key=lambda d:-d[1])
        for d in debts:
            d[0]*=1+d[1]/12
            p=min(d[0],pay); d[0]-=p; pay-=p
        debts=[d for d in debts if d[0]>1]; cash+=pay
        # casa
        if house_when=='first' and not house:
            need=HOUSE*(1+BUY)
            if sell_a and not log:  # con lo de A, préstamo por la diferencia
                loan=max(0,need-cash); cash=max(0,cash-need); debts.append([loan,R_H]); house=True; log.append((y,m,f"casa, préstamo {loan:,.0f}"))
            elif not sell_a and cash>=HOUSE*(0.25+BUY):
                cash-=HOUSE*(0.25+BUY); debts.append([HOUSE*0.75,R_H]); house=True; log.append((y,m,f"casa 75%, préstamo {HOUSE*0.75:,.0f}"))
        # unidades
        if unit_rule and (house or house_when is None):
            if unit_rule[0]=='lev' and cash>=U*(1-unit_rule[1]+BUY):
                cash-=U*(1-unit_rule[1]+BUY); debts.append([U*unit_rule[1],R_U]); extra+=1; log.append((y,m,f"unidad #{extra} al {unit_rule[1]:.0%}"))
            elif unit_rule[0]=='cash' and cash>=U*(1+BUY):
                cash-=U*(1+BUY); extra+=1; log.append((y,m,f"unidad #{extra} contado"))
        m+=1
        if m==13: y+=1; m=1
    n_units=sum(units.values())+extra+(1 if house else 0)
    m2=sum(units.values())*M2+extra*M2+(HOUSE_M2 if house else 0)
    debt=sum(d[0] for d in debts)
    eq=sum(units.values())*142500+extra*U+(HOUSE if house else 0)-debt+cash
    return name,log,n_units,m2,round(debt),round(eq),round(cash)
runs=[
 sim("B: vender A, casa 2028, luego unidades al contado",0,True,'first',('cash',)),
 sim("B': vender A, casa 2028, luego unidades al 75%",0,True,'first',('lev',0.75)),
 sim("C: no vender, casa 75% (2030), luego unidades al 75%",0,False,'first',('lev',0.75)),
 sim("F: alquilar para vivir (US$ 1.330), nunca casa, unidades al 75%",1330,False,None,('lev',0.75)),
 sim("F': alquilar para vivir, unidades al contado",1330,False,None,('cash',)),
]
print("Ahorro US$ 3.000/mes desde mar-2028, renta neta 495/unidad, precios planos. Restricción cuota/ingreso NO aplicada: ver columna cuota.\n")
for name,log,n,m2,debt,eq,cash in runs:
    print(name)
    for y,m,t in log: print(f"   {y}-{m:02d} {t}")
    print(f"   dic-2034: {n} unidades, {m2} m², deuda US$ {debt:,}, patrimonio US$ {eq:,}, efectivo {cash:,}\n")
print("Carry por unidad apalancada al 75%/15%: cuota", round(pmt(105000,0.15)), "vs renta 495 ->", round(495-pmt(105000,0.15)), "US$/mes;", "exige $", round(pmt(105000,0.15)*TC/0.25/1e6,1), "M por unidad")
