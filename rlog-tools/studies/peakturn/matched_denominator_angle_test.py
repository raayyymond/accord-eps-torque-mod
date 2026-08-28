import numpy as np
R={'1e':('V107',7.576,9.017),'21':('V111',1.007,3.137),'22':('V112',1.240,2.909),
   '23':('V112',1.060,8.320),'77':('V90',1.703,7.353),'78':('V91',1.067,3.719),
   '79':('V92',1.116,4.044),'7e':('V96',1.383,4.827),'7f':('V96',1.163,4.527),
   '85':('V100',2.277,6.510),'95':('V101',9.388,11.568),'96':('V102',4.554,8.868),
   '97':('STOCK',1.064,1.551),'9e':('V103',5.485,10.293),'a4':('V104',6.533,4.284),
   'a5':('V105',4.087,7.288),'a6':('V106',1.155,6.227)}
slo,shi=R['97'][1],R['97'][2]
print("CONFOUND: the RATIO's denominator varies 10x across builds (1.007 -> 9.388).")
print("A build already oscillating at small angle has less headroom, compressing its ratio.")
print("All three mod routes BELOW stock's 1.46x have small-angle p90 > 6.\n")
print("MATCHED ANALYSIS -- keep only mod routes whose SMALL-ANGLE p90 brackets stock's %.3f"%slo)
lo_w,hi_w=slo/1.7,slo*1.7
m=[(k,)+R[k] for k in R if R[k][0]!='STOCK' and lo_w<=R[k][1]<=hi_w]
m.sort(key=lambda x:x[3])
print("  window [%.3f, %.3f]  ->  n = %d matched mod routes\n"%(lo_w,hi_w,len(m)))
print("   route build   small-ang p90   LARGE-ang p90   ratio")
print("   r97   STOCK      %8.3f       %8.3f     %5.2fx   <-- STOCK"%(slo,shi,shi/slo))
for k,b,l,h in m:
    print("   r%-4s %-5s      %8.3f       %8.3f     %5.2fx"%(k,b,l,h,h/l))
hs=[x[3] for x in m]
n_above=sum(h>shi for h in hs)
print("\n  Stock small-angle %.3f sits at rank %d of %d in the matched set (well inside)."
      %(slo,sorted([x[2] for x in m]+[slo]).index(slo)+1,len(m)+1))
print("  \u21d2 exposure at small angle is MATCHED; only the large-angle response differs.\n")
print("  MOD large-angle p90 ABOVE stock's %.3f : %d of %d"%(shi,n_above,len(m)))
print("  matched mods' large-angle range: %.3f - %.3f   (stock %.3f)"%(min(hs),max(hs),shi))
print("  matched mods' ratio range      : %.2fx - %.2fx  (stock %.2fx)"
      %(min(x[3]/x[2] for x in m),max(x[3]/x[2] for x in m),shi/slo))
p=1.0/(len(m)+1)
print("\n  EXACT one-sided permutation p (stock is the minimum of %d) = 1/%d = %.3f"%(len(m)+1,len(m)+1,p))
print("  \U0001f6d1 With ONE stock route the p-value FLOOR is 1/(n_mod+1) = %.3f -- it CANNOT reach 0.05."%p)
k=2
print("  \u2705 With %d stock routes, all below all %d mods: p = %d!*%d!/%d! = %.4f  <-- clears 0.05"
      %(k,len(m),k,len(m),k+len(m),__import__("math").factorial(k)*__import__("math").factorial(len(m))/__import__("math").factorial(k+len(m))))
