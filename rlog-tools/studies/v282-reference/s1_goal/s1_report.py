"""Summaries from s1_results.json: tercile-matched gap tables, lag table, time-weighted importance, split-half."""
import json, numpy as np
H='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal/'
R=json.load(open(H+'s1_results.json')); C=R['cells']
GR=["V282","V282old","T64","T64B","T5","T4"]; VB=["2-8","8-15","15-22",">22"]
BA=["0.05-0.15","0.15-0.3","0.3-0.6","0.6-1.2","1.2-2.5"]; TE=["lo","mid","hi"]
def cell(g,vb,ba,t='all'):
    for c in C:
        if c['group']==g and c['vb']==vb and c['band']==ba and c['terc']==t: return c
out={}
print("== phasor lag (s, pose; act) and |Hc| pose, terc all")
for vb in VB:
    for ba in BA[:4]:
        row=f"{vb:5s} {ba:9s}"
        for g in GR:
            c=cell(g,vb,ba)
            if c: row+=f" {g}:{c['lag_pDa']:.2f}/{c['lag_aDa']:.2f} {c['Hc_pDa']:.2f}|"
        print(row)
print("\n== tercile-matched: rE_pD and G_pL, V282 vs T64 (CI) per terc")
for vb in VB:
    for ba in BA[:3]:
        for t in TE:
            a=cell("V282",vb,ba,t); b=cell("T64",vb,ba,t)
            if not a or not b: continue
            print(f"{vb:5s} {ba:9s} {t:3s} xrms V{a['x_rms']:.3f}/T{b['x_rms']:.3f} | rE V282 {a['rE_pD']:.2f}[{a['rE_pD_ci'][0]:.2f},{a['rE_pD_ci'][1]:.2f}] T64 {b['rE_pD']:.2f}[{b['rE_pD_ci'][0]:.2f},{b['rE_pD_ci'][1]:.2f}] | G V282 {a['G_pL']:.2f}[{a['G_pL_ci'][0]:.2f},{a['G_pL_ci'][1]:.2f}] T64 {b['G_pL']:.2f}[{b['G_pL_ci'][0]:.2f},{b['G_pL_ci'][1]:.2f}] | lag V{a['lag_pDa']:.2f} T{b['lag_pDa']:.2f} | sec {a['sec']:.0f}/{b['sec']:.0f}")
# importance: amplitude-matched excess error energy of group vs V282, per (vb, band), summed over terciles
print("\n== importance: amplitude-matched excess on-schedule error energy vs V282 (share of the group's total excess), and share of the group's own error energy")
imp={}
for g in ["T64","T64B","T5","T4","V282old"]:
    rows=[]; tot_err=0
    for vb in VB:
        for ba in BA:
            ex=0; err=0; sec=0
            for t in TE:
                a=cell("V282",vb,ba,t); b=cell(g,vb,ba,t)
                if not b: continue
                err+=b['errE_pD']; sec+=b['sec']
                if a: ex+=b['Sxx']*(b['rE_pD']**2-a['rE_pD']**2)
            rows.append((vb,ba,ex,err,sec)); tot_err+=err
    totex=sum(max(r[2],0) for r in rows)
    imp[g]=[dict(vb=r[0],band=r[1],excess_share=max(r[2],0)/totex,excess_raw=r[2]/tot_err,err_share=r[3]/tot_err,sec=r[4]) for r in rows]
    print(g)
    for r in sorted(imp[g],key=lambda z:-z['excess_share'])[:8]:
        print(f"   {r['vb']:5s} {r['band']:9s} excess {r['excess_share']*100:5.1f}%  (excess/own-total {r['excess_raw']*100:5.1f}%)  own-err-share {r['err_share']*100:5.1f}%  sec {r['sec']:.0f}")
json.dump(imp,open(H+'s1_importance.json','w'),indent=1)
print("\n== split-half G_pL / rE_pD, highway cells")
for vb in ["15-22",">22"]:
    for ba in BA[:3]:
        row=f"{vb:5s} {ba:9s}"
        for g in GR:
            c=cell(g,vb,ba)
            if c and None not in c["G_pL_half"]: row+=f" {g}: G {c["G_pL_half"][0]:.2f}/{c['G_pL_half'][1]:.2f} rE {c['rE_pD_half'][0]:.2f}/{c['rE_pD_half'][1]:.2f}|"
        print(row)
